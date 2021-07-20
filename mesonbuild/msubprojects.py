import os, subprocess
import argparse
import asyncio
import threading
import copy
import shutil
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
import typing as T

from . import mlog
from .mesonlib import quiet_git, GitException, Popen_safe, MesonException, windows_proof_rmtree
from .wrap.wrap import PackageDefinition, Resolver, WrapException, ALL_TYPES
from .wrap import wraptool

ALL_TYPES_STRING = ', '.join(ALL_TYPES)

class Logger:
    def __init__(self, total_tasks: int) -> None:
        self.lock = threading.Lock()
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.running_tasks = set()
        self.should_erase_line = ''

    def flush(self) -> None:
        if self.should_erase_line:
            print(self.should_erase_line, end='\r')
            self.should_erase_line = ''

    def print_progress(self) -> None:
        line = f'Progress: {self.completed_tasks} / {self.total_tasks}'
        max_len = shutil.get_terminal_size().columns - len(line)
        running = ', '.join(self.running_tasks)
        if len(running) + 3 > max_len:
            running = running[:max_len - 6] + '...'
        line = line + f' ({running})'
        print(self.should_erase_line, line, sep='', end='\r')
        self.should_erase_line = '\x1b[K'

    def start(self, wrap_name: str) -> None:
        with self.lock:
            self.running_tasks.add(wrap_name)
            self.print_progress()

    def done(self, wrap_name: str, log_queue: T.List[T.Tuple[mlog.TV_LoggableList, T.Any]]) -> None:
        with self.lock:
            self.flush()
            for args, kwargs in log_queue:
                mlog.log(*args, **kwargs)
            self.running_tasks.remove(wrap_name)
            self.completed_tasks += 1
            self.print_progress()


class Runner:
    def __init__(self, logger: Logger, r: Resolver, wrap: PackageDefinition, repo_dir: str, options: argparse.Namespace) -> None:
        # FIXME: Do a copy because Resolver.resolve() is stateful method that
        # cannot be called from multiple threads.
        self.wrap_resolver = copy.copy(r)
        self.wrap = wrap
        self.repo_dir = repo_dir
        self.options = options
        self.run_method = options.subprojects_func.__get__(self)
        self.log_queue = []
        self.logger = logger

    def log(self, *args, **kwargs):
        self.log_queue.append((args, kwargs))

    def run(self):
        self.logger.start(self.wrap.name)
        try:
            result = self.run_method()
        except MesonException as e:
            self.log(mlog.red('Error:'), str(e))
            result = False
        self.logger.done(self.wrap.name, self.log_queue)
        return result

    def update_wrapdb_file(self):
        try:
            patch_url = self.wrap.get('patch_url')
            branch, revision = wraptool.parse_patch_url(patch_url)
        except WrapException:
            return
        new_branch, new_revision = wraptool.get_latest_version(self.wrap.name)
        if new_branch != branch or new_revision != revision:
            wraptool.update_wrap_file(self.wrap.filename, self.wrap.name, new_branch, new_revision)
            self.log('  -> New wrap file downloaded.')

    def update_file(self):
        self.update_wrapdb_file()
        if not os.path.isdir(self.repo_dir):
            # The subproject is not needed, or it is a tarball extracted in
            # 'libfoo-1.0' directory and the version has been bumped and the new
            # directory is 'libfoo-2.0'. In that case forcing a meson
            # reconfigure will download and use the new tarball.
            self.log('  -> Not used.')
            return True
        elif self.options.reset:
            # Delete existing directory and redownload. It is possible that nothing
            # changed but we have no way to know. Hopefully tarballs are still
            # cached.
            windows_proof_rmtree(self.repo_dir)
            try:
                self.wrap_resolver.resolve(self.wrap.name, 'meson')
                self.log('  -> New version extracted')
                return True
            except WrapException as e:
                self.log('  ->', mlog.red(str(e)))
                return False
        else:
            # The subproject has not changed, or the new source and/or patch
            # tarballs should be extracted in the same directory than previous
            # version.
            self.log('  -> Subproject has not changed, or the new source/patch needs to be extracted on the same location.')
            self.log('     Pass --reset option to delete directory and redownload.')
            return False

    def git_output(self, cmd):
        return quiet_git(cmd, self.repo_dir, check=True)[1]

    def git_verbose(self, cmd):
        self.log(self.git_output(cmd))

    def git_stash(self):
        # That git command return 1 (failure) when there is something to stash.
        # We don't want to stash when there is nothing to stash because that would
        # print spurious "No local changes to save".
        if not quiet_git(['diff', '--quiet', 'HEAD'], self.repo_dir)[0]:
            # Don't pipe stdout here because we want the user to see their changes have
            # been saved.
            self.git_verbose(['stash'])

    def git_show(self):
        commit_message = self.git_output(['show', '--quiet', '--pretty=format:%h%n%d%n%s%n[%an]'])
        parts = [s.strip() for s in commit_message.split('\n')]
        self.log('  ->', mlog.yellow(parts[0]), mlog.red(parts[1]), parts[2], mlog.blue(parts[3]))

    def git_rebase(self, revision):
        try:
            self.git_output(['-c', 'rebase.autoStash=true', 'rebase', 'FETCH_HEAD'])
        except GitException as e:
            self.log('  -> Could not rebase', mlog.bold(self.repo_dir), 'onto', mlog.bold(revision))
            self.log(mlog.red(e.output))
            self.log(mlog.red(str(e)))
            return False
        return True

    def git_reset(self, revision):
        try:
            # Stash local changes, commits can always be found back in reflog, to
            # avoid any data lost by mistake.
            self.git_stash()
            self.git_output(['reset', '--hard', 'FETCH_HEAD'])
        except GitException as e:
            self.log('  -> Could not reset', mlog.bold(repo_dir), 'to', mlog.bold(revision))
            self.log(mlog.red(e.output))
            self.log(mlog.red(str(e)))
            return False
        return True

    def git_checkout(self, revision, create=False):
        cmd = ['checkout', '--ignore-other-worktrees', revision, '--']
        if create:
            cmd.insert('-b', 1)
        try:
            # Stash local changes, commits can always be found back in reflog, to
            # avoid any data lost by mistake.
            self.git_stash()
            self.git_output(cmd)
        except GitException as e:
            self.log('  -> Could not checkout', mlog.bold(revision), 'in', mlog.bold(self.repo_dir))
            self.log(mlog.red(e.output))
            self.log(mlog.red(str(e)))
            return False
        return True

    def git_checkout_and_reset(self, revision):
        # revision could be a branch that already exists but is outdated, so we still
        # have to reset after the checkout.
        success = self.git_checkout(revision)
        if success:
            success = self.git_reset(revision)
        return success

    def git_checkout_and_rebase(self, revision):
        # revision could be a branch that already exists but is outdated, so we still
        # have to rebase after the checkout.
        success = self.git_checkout(revision)
        if success:
            success = self.git_rebase(revision)
        return success

    def update_git(self):
        if not os.path.isdir(self.repo_dir):
            self.log('  -> Not used.')
            return True
        if not os.path.exists(os.path.join(self.repo_dir, '.git')):
            if self.options.reset:
                # Delete existing directory and redownload
                windows_proof_rmtree(self.repo_dir)
                try:
                    self.wrap_resolver.resolve(self.wrap.name, 'meson')
                    self.update_git_done()
                    return True
                except WrapException as e:
                    self.log('  ->', mlog.red(str(e)))
                    return False
            else:
                self.log('  -> Not a git repository.')
                self.log('Pass --reset option to delete directory and redownload.')
                return False
        revision = self.wrap.values.get('revision')
        url = self.wrap.values.get('url')
        push_url = self.wrap.values.get('push-url')
        if not revision or not url:
            # It could be a detached git submodule for example.
            self.log('  -> No revision or URL specified.')
            return True
        try:
            origin_url = self.git_output(['remote', 'get-url', 'origin']).strip()
        except GitException as e:
            self.log('  -> Failed to determine current origin URL in', mlog.bold(self.repo_dir))
            self.log(mlog.red(e.output))
            self.log(mlog.red(str(e)))
            return False
        if self.options.reset:
            try:
                self.git_output(['remote', 'set-url', 'origin', url])
                if push_url:
                    self.git_output(['remote', 'set-url', '--push', 'origin', push_url])
            except GitException as e:
                self.log('  -> Failed to reset origin URL in', mlog.bold(self.repo_dir))
                self.log(mlog.red(e.output))
                self.log(mlog.red(str(e)))
                return False
        elif url != origin_url:
            self.log(f'  -> URL changed from {origin_url!r} to {url!r}')
            return False
        try:
            # Same as `git branch --show-current` but compatible with older git version
            branch = self.git_output(['rev-parse', '--abbrev-ref', 'HEAD']).strip()
            branch = branch if branch != 'HEAD' else ''
        except GitException as e:
            self.log('  -> Failed to determine current branch in', mlog.bold(self.repo_dir))
            self.log(mlog.red(e.output))
            self.log(mlog.red(str(e)))
            return False
        try:
            # Fetch only the revision we need, this avoids fetching useless branches.
            # revision can be either a branch, tag or commit id. In all cases we want
            # FETCH_HEAD to be set to the desired commit and "git checkout <revision>"
            # to to either switch to existing/new branch, or detach to tag/commit.
            # It is more complicated than it first appear, see discussion there:
            # https://github.com/mesonbuild/meson/pull/7723#discussion_r488816189.
            heads_refmap = '+refs/heads/*:refs/remotes/origin/*'
            tags_refmap = '+refs/tags/*:refs/tags/*'
            self.git_output(['fetch', '--refmap', heads_refmap, '--refmap', tags_refmap, 'origin', revision])
        except GitException as e:
            self.log('  -> Could not fetch revision', mlog.bold(revision), 'in', mlog.bold(self.repo_dir))
            self.log(mlog.red(e.output))
            self.log(mlog.red(str(e)))
            return False

        if branch == '':
            # We are currently in detached mode
            if self.options.reset:
                success = self.git_checkout_and_reset(revision)
            else:
                success = self.git_checkout_and_rebase(revision)
        elif branch == revision:
            # We are in the same branch. A reset could still be needed in the case
            # a force push happened on remote repository.
            if self.options.reset:
                success = self.git_reset(revision)
            else:
                success = self.git_rebase(revision)
        else:
            # We are in another branch, either the user created their own branch and
            # we should rebase it, or revision changed in the wrap file and we need
            # to checkout the new branch.
            if self.options.reset:
                success = self.git_checkout_and_reset(revision)
            else:
                success = self.git_rebase(revision)
        if success:
            self.update_git_done()
        return success

    def update_git_done(self):
        self.git_output(['submodule', 'update', '--checkout', '--recursive'])
        self.git_show()

    def update_hg(self):
        if not os.path.isdir(self.repo_dir):
            self.log('  -> Not used.')
            return True
        revno = self.wrap.get('revision')
        if revno.lower() == 'tip':
            # Failure to do pull is not a fatal error,
            # because otherwise you can't develop without
            # a working net connection.
            subprocess.call(['hg', 'pull'], cwd=self.repo_dir)
        else:
            if subprocess.call(['hg', 'checkout', revno], cwd=self.repo_dir) != 0:
                subprocess.check_call(['hg', 'pull'], cwd=self.repo_dir)
                subprocess.check_call(['hg', 'checkout', revno], cwd=self.repo_dir)
        return True

    def update_svn(self):
        if not os.path.isdir(self.repo_dir):
            self.log('  -> Not used.')
            return True
        revno = self.wrap.get('revision')
        p, out, _ = Popen_safe(['svn', 'info', '--show-item', 'revision', self.repo_dir])
        current_revno = out
        if current_revno == revno:
            return True
        if revno.lower() == 'head':
            # Failure to do pull is not a fatal error,
            # because otherwise you can't develop without
            # a working net connection.
            subprocess.call(['svn', 'update'], cwd=self.repo_dir)
        else:
            subprocess.check_call(['svn', 'update', '-r', revno], cwd=self.repo_dir)
        return True

    def update(self):
        self.log(f'Updating {self.wrap.name}...')
        if self.wrap.type == 'file':
            return self.update_file()
        elif self.wrap.type == 'git':
            return self.update_git()
        elif self.wrap.type == 'hg':
            return self.update_hg()
        elif self.wrap.type == 'svn':
            return self.update_svn()
        elif self.wrap.type is None:
            self.log('  -> Cannot update subproject with no wrap file')
        else:
            self.log('  -> Cannot update', self.wrap.type, 'subproject')
        return True

    def checkout(self):
        if self.wrap.type != 'git' or not os.path.isdir(self.repo_dir):
            return True
        branch_name = self.options.branch_name if self.options.branch_name else self.wrap.get('revision')
        if not branch_name:
            # It could be a detached git submodule for example.
            return True
        self.log(f'Checkout {branch_name} in {self.wrap.name}...')
        if self.git_checkout(branch_name, create=self.options.b):
            self.git_show()
            return True
        return False

    def download(self):
        self.log(f'Download {self.wrap.name}...')
        if os.path.isdir(self.repo_dir):
            self.log('  -> Already downloaded')
            return True
        try:
            self.wrap_resolver.resolve(self.wrap.name, 'meson')
            self.log('  -> done')
        except WrapException as e:
            self.log('  ->', mlog.red(str(e)))
            return False
        return True

    def foreach(self):
        self.log(f'Executing command in {self.repo_dir}')
        if not os.path.isdir(self.repo_dir):
            self.log('  -> Not downloaded yet')
            return True
        cmd = [self.options.command] + self.options.args
        p, out, _ = Popen_safe(cmd, stderr=subprocess.STDOUT, cwd=self.repo_dir)
        if p.returncode != 0:
            err_message = "Command '{}' returned non-zero exit status {}.".format(" ".join(cmd), p.returncode)
            self.log('  -> ', mlog.red(err_message))
            self.log(out, end='')
            return False

        self.log(out, end='')
        return True

    def purge(self) -> bool:
        # if subproject is not wrap-based, then don't remove it
        if not self.wrap.type:
            return True

        if self.wrap.redirected:
            redirect_file = Path(self.wrap.original_filename).resolve()
            if self.options.confirm:
                redirect_file.unlink()
            mlog.log(f'Deleting {redirect_file}')

        if self.wrap.type == 'redirect':
            redirect_file = Path(self.wrap.filename).resolve()
            if self.options.confirm:
                redirect_file.unlink()
            self.log(f'Deleting {redirect_file}')

        if self.options.include_cache:
            packagecache = Path(self.wrap_resolver.cachedir).resolve()
            try:
                subproject_cache_file = packagecache / self.wrap.get("source_filename")
                if subproject_cache_file.is_file():
                    if self.options.confirm:
                        subproject_cache_file.unlink()
                    self.log(f'Deleting {subproject_cache_file}')
            except WrapException:
                pass

            try:
                subproject_patch_file = packagecache / self.wrap.get("patch_filename")
                if subproject_patch_file.is_file():
                    if self.options.confirm:
                        subproject_patch_file.unlink()
                    self.log(f'Deleting {subproject_patch_file}')
            except WrapException:
                pass

            # Don't log that we will remove an empty directory. Since purge is
            # parallelized, another thread could have deleted it already.
            try:
                if not any(packagecache.iterdir()):
                    windows_proof_rmtree(str(packagecache))
            except FileNotFoundError:
                pass

        subproject_source_dir = Path(self.repo_dir).resolve()

        # Don't follow symlink. This is covered by the next if statement, but why
        # not be doubly sure.
        if subproject_source_dir.is_symlink():
            if self.options.confirm:
                subproject_source_dir.unlink()
            self.log(f'Deleting {subproject_source_dir}')
            return True
        if not subproject_source_dir.is_dir():
            return True

        try:
            if self.options.confirm:
                windows_proof_rmtree(str(subproject_source_dir))
            self.log(f'Deleting {subproject_source_dir}')
        except OSError as e:
            mlog.error(f'Unable to remove: {subproject_source_dir}: {e}')
            return False

        return True

    @staticmethod
    def post_purge(options):
        if not options.confirm:
            mlog.log('')
            mlog.log('Nothing has been deleted, run again with --confirm to apply.')

def add_common_arguments(p):
    p.add_argument('--sourcedir', default='.',
                   help='Path to source directory')
    p.add_argument('--types', default='',
                   help=f'Comma-separated list of subproject types. Supported types are: {ALL_TYPES_STRING} (default: all)')
    p.add_argument('--num-processes', default=None, type=int,
                   help='How many parallel processes to use (Since 0.59.0).')

def add_subprojects_argument(p):
    p.add_argument('subprojects', nargs='*',
                   help='List of subprojects (default: all)')

def add_arguments(parser):
    subparsers = parser.add_subparsers(title='Commands', dest='command')
    subparsers.required = True

    p = subparsers.add_parser('update', help='Update all subprojects from wrap files')
    p.add_argument('--rebase', default=True, action='store_true',
                   help='Rebase your branch on top of wrap\'s revision. ' + \
                        'Deprecated, it is now the default behaviour. (git only)')
    p.add_argument('--reset', default=False, action='store_true',
                   help='Checkout wrap\'s revision and hard reset to that commit. (git only)')
    add_common_arguments(p)
    add_subprojects_argument(p)
    p.set_defaults(subprojects_func=Runner.update)

    p = subparsers.add_parser('checkout', help='Checkout a branch (git only)')
    p.add_argument('-b', default=False, action='store_true',
                   help='Create a new branch')
    p.add_argument('branch_name', nargs='?',
                   help='Name of the branch to checkout or create (default: revision set in wrap file)')
    add_common_arguments(p)
    add_subprojects_argument(p)
    p.set_defaults(subprojects_func=Runner.checkout)

    p = subparsers.add_parser('download', help='Ensure subprojects are fetched, even if not in use. ' +
                                               'Already downloaded subprojects are not modified. ' +
                                               'This can be used to pre-fetch all subprojects and avoid downloads during configure.')
    add_common_arguments(p)
    add_subprojects_argument(p)
    p.set_defaults(subprojects_func=Runner.download)

    p = subparsers.add_parser('foreach', help='Execute a command in each subproject directory.')
    p.add_argument('command', metavar='command ...',
                   help='Command to execute in each subproject directory')
    p.add_argument('args', nargs=argparse.REMAINDER,
                   help=argparse.SUPPRESS)
    add_common_arguments(p)
    p.set_defaults(subprojects=[])
    p.set_defaults(subprojects_func=Runner.foreach)

    p = subparsers.add_parser('purge', help='Remove all wrap-based subproject artifacts')
    add_common_arguments(p)
    add_subprojects_argument(p)
    p.add_argument('--include-cache', action='store_true', default=False, help='Remove the package cache as well')
    p.add_argument('--confirm', action='store_true', default=False, help='Confirm the removal of subproject artifacts')
    p.set_defaults(subprojects_func=Runner.purge)
    p.set_defaults(post_func=Runner.post_purge)

def run(options):
    src_dir = os.path.relpath(os.path.realpath(options.sourcedir))
    if not os.path.isfile(os.path.join(src_dir, 'meson.build')):
        mlog.error('Directory', mlog.bold(src_dir), 'does not seem to be a Meson source directory.')
        return 1
    subprojects_dir = os.path.join(src_dir, 'subprojects')
    if not os.path.isdir(subprojects_dir):
        mlog.log('Directory', mlog.bold(src_dir), 'does not seem to have subprojects.')
        return 0
    r = Resolver(src_dir, 'subprojects')
    if options.subprojects:
        wraps = [wrap for name, wrap in r.wraps.items() if name in options.subprojects]
    else:
        wraps = r.wraps.values()
    types = [t.strip() for t in options.types.split(',')] if options.types else []
    for t in types:
        if t not in ALL_TYPES:
            raise MesonException(f'Unknown subproject type {t!r}, supported types are: {ALL_TYPES_STRING}')
    tasks = []
    task_names = []
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(options.num_processes)
    if types:
        wraps = [wrap for wrap in wraps if wrap.type in types]
    logger = Logger(len(wraps))
    for wrap in wraps:
        dirname = Path(subprojects_dir, wrap.directory).as_posix()
        runner = Runner(logger, r, wrap, dirname, options)
        task = loop.run_in_executor(executor, runner.run)
        tasks.append(task)
        task_names.append(wrap.name)
    results = loop.run_until_complete(asyncio.gather(*tasks))
    logger.flush()
    post_func = getattr(options, 'post_func', None)
    if post_func:
        post_func(options)
    failures = [name for name, success in zip(task_names, results) if not success]
    if failures:
        m = 'Please check logs above as command failed in some subprojects which could have been left in conflict state: '
        m += ', '.join(failures)
        mlog.warning(m)
    return len(failures)
