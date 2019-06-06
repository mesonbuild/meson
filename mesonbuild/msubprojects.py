import os, subprocess
import argparse

from . import mlog
from .mesonlib import Popen_safe
from .wrap.wrap import API_ROOT, PackageDefinition, Resolver, WrapException
from .wrap import wraptool

def update_wrapdb_file(wrap, repo_dir, options):
    patch_url = wrap.get('patch_url')
    branch, revision = wraptool.parse_patch_url(patch_url)
    new_branch, new_revision = wraptool.get_latest_version(wrap.name)
    if new_branch == branch and new_revision == revision:
        mlog.log('  -> Up to date.')
        return
    wraptool.update_wrap_file(wrap.filename, wrap.name, new_branch, new_revision)
    msg = ['  -> New wrap file downloaded.']
    # Meson reconfigure won't use the new wrap file as long as the source
    # directory exists. We don't delete it ourself to avoid data loss in case
    # user has changes in their copy.
    if os.path.isdir(repo_dir):
        msg += ['To use it, delete', mlog.bold(repo_dir), 'and run', mlog.bold('meson --reconfigure')]
    mlog.log(*msg)

def update_file(wrap, repo_dir, options):
    patch_url = wrap.values.get('patch_url', '')
    if patch_url.startswith(API_ROOT):
        update_wrapdb_file(wrap, repo_dir, options)
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

def git(cmd, workingdir):
    return subprocess.check_output(['git', '-C', workingdir] + cmd,
                                   stderr=subprocess.STDOUT).decode()

def git_show(repo_dir):
    commit_message = git(['show', '--quiet', '--pretty=format:%h%n%d%n%s%n[%an]'], repo_dir)
    parts = [s.strip() for s in commit_message.split('\n')]
    mlog.log('  ->', mlog.yellow(parts[0]), mlog.red(parts[1]), parts[2], mlog.blue(parts[3]))

def update_git(wrap, repo_dir, options):
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not used.')
        return
    revision = wrap.get('revision')
    ret = git(['rev-parse', '--abbrev-ref', 'HEAD'], repo_dir).strip()
    if ret == 'HEAD':
        try:
            # We are currently in detached mode, just checkout the new revision
            git(['fetch'], repo_dir)
            git(['checkout', revision], repo_dir)
        except subprocess.CalledProcessError as e:
            out = e.output.decode().strip()
            mlog.log('  -> Could not checkout revision', mlog.cyan(revision))
            mlog.log(mlog.red(out))
            mlog.log(mlog.red(str(e)))
            return
    elif ret == revision:
        try:
            # We are in the same branch, pull latest commits
            git(['-c', 'rebase.autoStash=true', 'pull', '--rebase'], repo_dir)
        except subprocess.CalledProcessError as e:
            out = e.output.decode().strip()
            mlog.log('  -> Could not rebase', mlog.bold(repo_dir), 'please fix and try again.')
            mlog.log(mlog.red(out))
            mlog.log(mlog.red(str(e)))
            return
    else:
        # We are in another branch, probably user created their own branch and
        # we should rebase it on top of wrap's branch.
        if options.rebase:
            try:
                git(['fetch'], repo_dir)
                git(['-c', 'rebase.autoStash=true', 'rebase', revision], repo_dir)
            except subprocess.CalledProcessError as e:
                out = e.output.decode().strip()
                mlog.log('  -> Could not rebase', mlog.bold(repo_dir), 'please fix and try again.')
                mlog.log(mlog.red(out))
                mlog.log(mlog.red(str(e)))
                return
        else:
            mlog.log('  -> Target revision is', mlog.bold(revision), 'but currently in branch is', mlog.bold(ret), '\n' +
                     '     To rebase your branch on top of', mlog.bold(revision), 'use', mlog.bold('--rebase'), 'option.')
            return

    git(['submodule', 'update', '--checkout', '--recursive'], repo_dir)
    git_show(repo_dir)

def update_hg(wrap, repo_dir, options):
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not used.')
        return
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

def update_svn(wrap, repo_dir, options):
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not used.')
        return
    revno = wrap.get('revision')
    p, out, _ = Popen_safe(['svn', 'info', '--show-item', 'revision', repo_dir])
    current_revno = out
    if current_revno == revno:
        return
    if revno.lower() == 'head':
        # Failure to do pull is not a fatal error,
        # because otherwise you can't develop without
        # a working net connection.
        subprocess.call(['svn', 'update'], cwd=repo_dir)
    else:
        subprocess.check_call(['svn', 'update', '-r', revno], cwd=repo_dir)

def update(wrap, repo_dir, options):
    mlog.log('Updating %s...' % wrap.name)
    if wrap.type == 'file':
        update_file(wrap, repo_dir, options)
    elif wrap.type == 'git':
        update_git(wrap, repo_dir, options)
    elif wrap.type == 'hg':
        update_hg(wrap, repo_dir, options)
    elif wrap.type == 'svn':
        update_svn(wrap, repo_dir, options)
    else:
        mlog.log('  -> Cannot update', wrap.type, 'subproject')

def checkout(wrap, repo_dir, options):
    if wrap.type != 'git' or not os.path.isdir(repo_dir):
        return
    branch_name = options.branch_name if options.branch_name else wrap.get('revision')
    cmd = ['checkout', branch_name, '--']
    if options.b:
        cmd.insert(1, '-b')
    mlog.log('Checkout %s in %s...' % (branch_name, wrap.name))
    try:
        git(cmd, repo_dir)
        git_show(repo_dir)
    except subprocess.CalledProcessError as e:
        out = e.output.decode().strip()
        mlog.log('  -> ', mlog.red(out))

def download(wrap, repo_dir, options):
    mlog.log('Download %s...' % wrap.name)
    if os.path.isdir(repo_dir):
        mlog.log('  -> Already downloaded')
        return
    try:
        r = Resolver(os.path.dirname(repo_dir))
        r.resolve(wrap.name, 'meson')
        mlog.log('  -> done')
    except WrapException as e:
        mlog.log('  ->', mlog.red(str(e)))

def foreach(wrap, repo_dir, options):
    mlog.log('Executing command in %s' % repo_dir)
    if not os.path.isdir(repo_dir):
        mlog.log('  -> Not downloaded yet')
        return
    try:
        subprocess.check_call([options.command] + options.args, cwd=repo_dir)
        mlog.log('')
    except subprocess.CalledProcessError as e:
        out = e.output.decode().strip()
        mlog.log('  -> ', mlog.red(out))

def add_common_arguments(p):
    p.add_argument('--sourcedir', default='.',
                   help='Path to source directory')
    p.add_argument('subprojects', nargs='*',
                   help='List of subprojects (default: all)')

def add_arguments(parser):
    subparsers = parser.add_subparsers(title='Commands', dest='command')
    subparsers.required = True

    p = subparsers.add_parser('update', help='Update all subprojects from wrap files')
    p.add_argument('--rebase', default=False, action='store_true',
                   help='Rebase your branch on top of wrap\'s revision (git only)')
    add_common_arguments(p)
    p.set_defaults(subprojects_func=update)

    p = subparsers.add_parser('checkout', help='Checkout a branch (git only)')
    p.add_argument('-b', default=False, action='store_true',
                   help='Create a new branch')
    p.add_argument('branch_name', nargs='?',
                   help='Name of the branch to checkout or create (default: revision set in wrap file)')
    add_common_arguments(p)
    p.set_defaults(subprojects_func=checkout)

    p = subparsers.add_parser('download', help='Ensure subprojects are fetched, even if not in use. ' +
                                               'Already downloaded subprojects are not modified. ' +
                                               'This can be used to pre-fetch all subprojects and avoid downloads during configure.')
    add_common_arguments(p)
    p.set_defaults(subprojects_func=download)

    p = subparsers.add_parser('foreach', help='Execute a command in each subproject directory.')
    p.add_argument('command', metavar='command ...',
                   help='Command to execute in each subproject directory')
    p.add_argument('args', nargs=argparse.REMAINDER,
                   help=argparse.SUPPRESS)
    p.add_argument('--sourcedir', default='.',
                   help='Path to source directory')
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
    files = []
    if hasattr(options, 'subprojects'):
        for name in options.subprojects:
            f = os.path.join(subprojects_dir, name + '.wrap')
            if not os.path.isfile(f):
                mlog.error('Subproject', mlog.bold(name), 'not found.')
                return 1
            else:
                files.append(f)
    if not files:
        for f in os.listdir(subprojects_dir):
            if f.endswith('.wrap'):
                files.append(os.path.join(subprojects_dir, f))
    for f in files:
        wrap = PackageDefinition(f)
        directory = wrap.values.get('directory', wrap.name)
        repo_dir = os.path.join(subprojects_dir, directory)
        options.subprojects_func(wrap, repo_dir, options)
    return 0
