import os, subprocess
import argparse
from ._pathlib import Path

from . import mlog
from .mesonlib import quiet_git, verbose_git, GitException, Popen_safe, MesonException, windows_proof_rmtree
from .wrap.wrap import API_ROOT, Resolver, WrapException, ALL_TYPES
from .wrap import wraptool

ALL_TYPES_STRING = ', '.join(ALL_TYPES)

def update_wrapdb_file(wrap, repo_dir, options):
    patch_url = wrap.get('patch_url')
    branch, revision = wraptool.parse_patch_url(patch_url)
    new_branch, new_revision = wraptool.get_latest_version(wrap.name)
    if new_branch == branch and new_revision == revision:
        mlog.log('  -> Up to date.')
        return True
    wraptool.update_wrap_file(wrap.filename, wrap.name, new_branch, new_revision)
    msg = ['  -> New wrap file downloaded.']
    # Meson reconfigure won't use the new wrap file as long as the source
    # directory exists. We don't delete it ourself to avoid data loss in case
    # user has changes in their copy.
    if os.path.isdir(repo_dir):
        msg += ['To use it, delete', mlog.bold(repo_dir), 'and run', mlog.bold('meson --reconfigure')]
    mlog.log(*msg)
    return True

def update_file(r, wrap, repo_dir, options):
    patch_url = wrap.values.get('patch_url', '')
    if patch_url.startswith(API_ROOT):
        return update_wrapdb_file(wrap, repo_dir, options)
    elif not os.path.isdir(repo_dir):
        # The subproject is not needed, or it is a tarball extracted in
        # 'libfoo-1.0' directory and the version has been bumped and the new
        # directory is 'libfoo-2.0'. In that case forcing a meson
        # reconfigure will download and use the new tarball.
        mlog.log('  -> Subproject has not been checked out. Run', mlog.bold('meson --reconfigure'), 'to fetch it if needed.')
    else:
        # The subproject has not changed, or the new source and/or patch
        # tarballs should be extracted in the same directory than previous
        # version.
        mlog.log('  -> Subproject has not changed, or the new source/patch needs to be extracted on the same location.\n' +
                 '     In that case, delete', mlog.bold(repo_dir), 'and run', mlog.bold('meson --reconfigure'))
    return True

def git_output(cmd, workingdir):
    return quiet_git(cmd, workingdir, check=True)[1]

def git_stash(workingdir):
    # That git command return 1 (failure) when there is something to stash.
    # We don't want to stash when there is nothing to stash because that would
    # print spurious "No local changes to save".
    if not quiet_git(['diff', '--quiet', 'HEAD'], workingdir)[0]:
        # Don't pipe stdout here because we want the user to see their changes have
        # been saved.
        verbose_git(['stash'], workingdir, check=True)

def git_show(repo_dir):
    commit_message = git_output(['show', '--quiet', '--pretty=format:%h%n%d%n%s%n[%an]'], repo_dir)
    parts = [s.strip() for s in commit_message.split('\n')]
    mlog.log('  ->', mlog.yellow(parts[0]), mlog.red(parts[1]), parts[2], mlog.blue(parts[3]))

def git_rebase(repo_dir, revision):
    try:
        git_output(['-c', 'rebase.autoStash=true', 'rebase', 'FETCH_HEAD'], repo_dir)
    except GitException as e:
        mlog.log('  -> Could not rebase', mlog.bold(repo_dir), 'onto', mlog.bold(revision))
        mlog.log(mlog.red(e.output))
        mlog.log(mlog.red(str(e)))
        return False
    return True

def git_reset(repo_dir, revision):
    try:
        # Stash local changes, commits can always be found back in reflog, to
        # avoid any data lost by mistake.
        git_stash(repo_dir)
        git_output(['reset', '--hard', 'FETCH_HEAD'], repo_dir)
    except GitException as e:
        mlog.log('  -> Could not reset', mlog.bold(repo_dir), 'to', mlog.bold(revision))
        mlog.log(mlog.red(e.output))
        mlog.log(mlog.red(str(e)))
        return False
    return True

def git_checkout(repo_dir, revision, create=False):
    cmd = ['checkout', revision, '--']
    if create:
        cmd.insert('-b', 1)
    try:
        # Stash local changes, commits can always be found back in reflog, to
        # avoid any data lost by mistake.
        git_stash(repo_dir)
        git_output(cmd, repo_dir)
    except GitException as e:
        mlog.log('  -> Could not checkout', mlog.bold(revision), 'in', mlog.bold(repo_dir))
        mlog.log(mlog.red(e.output))
        mlog.log(mlog.red(str(e)))
        return False
    return True

def git_checkout_and_reset(repo_dir, revision):
    # revision could be a branch that already exists but is outdated, so we still
    # have to reset after the checkout.
    success = git_checkout(repo_dir, revision)
    if success:
        success = git_reset(repo_dir, revision)
    return success

def git_checkout_and_rebase(repo_dir, revision):
    # revision could be a branch that already exists but is outdated, so we still
    # have to rebase after the checkout.
    success = git_checkout(repo_dir, revision)
    if success:
        success = git_rebase(repo_dir, revision)
    return success

def update_git(r, wrap, repo_dir, options):
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not used.')
        return True
    if not os.path.exists(os.path.join(repo_dir, '.git')):
        if options.reset:
            # Delete existing directory and redownload
            windows_proof_rmtree(repo_dir)
            try:
                r.resolve(wrap.name, 'meson')
                update_git_done(repo_dir)
                return True
            except WrapException as e:
                mlog.log('  ->', mlog.red(str(e)))
                return False
        else:
            mlog.log('  -> Not a git repository.')
            mlog.log('Pass --reset option to delete directory and redownload.')
            return False
    revision = wrap.values.get('revision')
    url = wrap.values.get('url')
    push_url = wrap.values.get('push-url')
    if not revision or not url:
        # It could be a detached git submodule for example.
        mlog.log('  -> No revision or URL specified.')
        return True
    try:
        origin_url = git_output(['remote', 'get-url', 'origin'], repo_dir).strip()
    except GitException as e:
        mlog.log('  -> Failed to determine current origin URL in', mlog.bold(repo_dir))
        mlog.log(mlog.red(e.output))
        mlog.log(mlog.red(str(e)))
        return False
    if options.reset:
        try:
            git_output(['remote', 'set-url', 'origin', url], repo_dir)
            if push_url:
                git_output(['remote', 'set-url', '--push', 'origin', push_url], repo_dir)
        except GitException as e:
            mlog.log('  -> Failed to reset origin URL in', mlog.bold(repo_dir))
            mlog.log(mlog.red(e.output))
            mlog.log(mlog.red(str(e)))
            return False
    elif url != origin_url:
        mlog.log('  -> URL changed from {!r} to {!r}'.format(origin_url, url))
        return False
    try:
        # Same as `git branch --show-current` but compatible with older git version
        branch = git_output(['rev-parse', '--abbrev-ref', 'HEAD'], repo_dir).strip()
        branch = branch if branch != 'HEAD' else ''
    except GitException as e:
        mlog.log('  -> Failed to determine current branch in', mlog.bold(repo_dir))
        mlog.log(mlog.red(e.output))
        mlog.log(mlog.red(str(e)))
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
        git_output(['fetch', '--refmap', heads_refmap, '--refmap', tags_refmap, 'origin', revision], repo_dir)
    except GitException as e:
        mlog.log('  -> Could not fetch revision', mlog.bold(revision), 'in', mlog.bold(repo_dir))
        mlog.log(mlog.red(e.output))
        mlog.log(mlog.red(str(e)))
        return False

    if branch == '':
        # We are currently in detached mode
        if options.reset:
            success = git_checkout_and_reset(repo_dir, revision)
        else:
            success = git_checkout_and_rebase(repo_dir, revision)
    elif branch == revision:
        # We are in the same branch. A reset could still be needed in the case
        # a force push happened on remote repository.
        if options.reset:
            success = git_reset(repo_dir, revision)
        else:
            success = git_rebase(repo_dir, revision)
    else:
        # We are in another branch, either the user created their own branch and
        # we should rebase it, or revision changed in the wrap file and we need
        # to checkout the new branch.
        if options.reset:
            success = git_checkout_and_reset(repo_dir, revision)
        else:
            success = git_rebase(repo_dir, revision)
    if success:
        update_git_done(repo_dir)
    return success

def update_git_done(repo_dir):
    git_output(['submodule', 'update', '--checkout', '--recursive'], repo_dir)
    git_show(repo_dir)

def update_hg(r, wrap, repo_dir, options):
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not used.')
        return True
    revno = wrap.get('revision')
    if revno.lower() == 'tip':
        # Failure to do pull is not a fatal error,
        # because otherwise you can't develop without
        # a working net connection.
        subprocess.call(['hg', 'pull'], cwd=repo_dir)
    else:
        if subprocess.call(['hg', 'checkout', revno], cwd=repo_dir) != 0:
            subprocess.check_call(['hg', 'pull'], cwd=repo_dir)
            subprocess.check_call(['hg', 'checkout', revno], cwd=repo_dir)
    return True

def update_svn(r, wrap, repo_dir, options):
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not used.')
        return True
    revno = wrap.get('revision')
    p, out, _ = Popen_safe(['svn', 'info', '--show-item', 'revision', repo_dir])
    current_revno = out
    if current_revno == revno:
        return True
    if revno.lower() == 'head':
        # Failure to do pull is not a fatal error,
        # because otherwise you can't develop without
        # a working net connection.
        subprocess.call(['svn', 'update'], cwd=repo_dir)
    else:
        subprocess.check_call(['svn', 'update', '-r', revno], cwd=repo_dir)
    return True

def update(r, wrap, repo_dir, options):
    mlog.log('Updating {}...'.format(wrap.name))
    if wrap.type == 'file':
        return update_file(r, wrap, repo_dir, options)
    elif wrap.type == 'git':
        return update_git(r, wrap, repo_dir, options)
    elif wrap.type == 'hg':
        return update_hg(r, wrap, repo_dir, options)
    elif wrap.type == 'svn':
        return update_svn(r, wrap, repo_dir, options)
    else:
        mlog.log('  -> Cannot update', wrap.type, 'subproject')
    return True

def checkout(r, wrap, repo_dir, options):
    if wrap.type != 'git' or not os.path.isdir(repo_dir):
        return True
    branch_name = options.branch_name if options.branch_name else wrap.get('revision')
    if not branch_name:
        # It could be a detached git submodule for example.
        return True
    mlog.log('Checkout {} in {}...'.format(branch_name, wrap.name))
    if git_checkout(repo_dir, branch_name, create=options.b):
        git_show(repo_dir)
        return True
    return False

def download(r, wrap, repo_dir, options):
    mlog.log('Download {}...'.format(wrap.name))
    if os.path.isdir(repo_dir):
        mlog.log('  -> Already downloaded')
        return True
    try:
        r.resolve(wrap.name, 'meson')
        mlog.log('  -> done')
    except WrapException as e:
        mlog.log('  ->', mlog.red(str(e)))
        return False
    return True

def foreach(r, wrap, repo_dir, options):
    mlog.log('Executing command in {}'.format(repo_dir))
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not downloaded yet')
        return True
    cmd = [options.command] + options.args
    p, out, _ = Popen_safe(cmd, stderr=subprocess.STDOUT, cwd=repo_dir)
    if p.returncode != 0:
        err_message = "Command '{}' returned non-zero exit status {}.".format(" ".join(cmd), p.returncode)
        mlog.log('  -> ', mlog.red(err_message))
        mlog.log(out, end='')
        return False

    mlog.log(out, end='')
    return True

def add_common_arguments(p):
    p.add_argument('--sourcedir', default='.',
                   help='Path to source directory')
    p.add_argument('--types', default='',
                   help='Comma-separated list of subproject types. Supported types are: {} (default: all)'.format(ALL_TYPES_STRING))

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
    p.set_defaults(subprojects_func=update)

    p = subparsers.add_parser('checkout', help='Checkout a branch (git only)')
    p.add_argument('-b', default=False, action='store_true',
                   help='Create a new branch')
    p.add_argument('branch_name', nargs='?',
                   help='Name of the branch to checkout or create (default: revision set in wrap file)')
    add_common_arguments(p)
    add_subprojects_argument(p)
    p.set_defaults(subprojects_func=checkout)

    p = subparsers.add_parser('download', help='Ensure subprojects are fetched, even if not in use. ' +
                                               'Already downloaded subprojects are not modified. ' +
                                               'This can be used to pre-fetch all subprojects and avoid downloads during configure.')
    add_common_arguments(p)
    add_subprojects_argument(p)
    p.set_defaults(subprojects_func=download)

    p = subparsers.add_parser('foreach', help='Execute a command in each subproject directory.')
    p.add_argument('command', metavar='command ...',
                   help='Command to execute in each subproject directory')
    p.add_argument('args', nargs=argparse.REMAINDER,
                   help=argparse.SUPPRESS)
    add_common_arguments(p)
    p.set_defaults(subprojects=[])
    p.set_defaults(subprojects_func=foreach)

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
            raise MesonException('Unknown subproject type {!r}, supported types are: {}'.format(t, ALL_TYPES_STRING))
    failures = []
    for wrap in wraps:
        if types and wrap.type not in types:
            continue
        dirname = Path(subprojects_dir, wrap.directory).as_posix()
        if not options.subprojects_func(r, wrap, dirname, options):
            failures.append(wrap.name)
    if failures:
        m = 'Please check logs above as command failed in some subprojects which could have been left in conflict state: '
        m += ', '.join(failures)
        mlog.warning(m)
    return len(failures)
