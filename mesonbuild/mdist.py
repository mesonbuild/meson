# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import gzip
import os
import sys
import shutil
import subprocess
import tarfile
import tempfile
import hashlib
import json
from glob import glob
from pathlib import Path
from mesonbuild.environment import detect_ninja
from mesonbuild.mesonlib import (MesonException, RealPathAction, quiet_git,
                                 windows_proof_rmtree, setup_vsenv)
from mesonbuild.wrap import wrap
from mesonbuild import mlog, build
from .scripts.meson_exe import run_exe

archive_choices = ['gztar', 'xztar', 'zip']

archive_extension = {'gztar': '.tar.gz',
                     'xztar': '.tar.xz',
                     'zip': '.zip'}

def add_arguments(parser):
    parser.add_argument('-C', dest='wd', action=RealPathAction,
                        help='directory to cd into before running')
    parser.add_argument('--formats', default='xztar',
                        help='Comma separated list of archive types to create. Supports xztar (default), gztar, and zip.')
    parser.add_argument('--include-subprojects', action='store_true',
                        help='Include source code of subprojects that have been used for the build.')
    parser.add_argument('--no-tests', action='store_true',
                        help='Do not build and test generated packages.')


def create_hash(fname):
    hashname = fname + '.sha256sum'
    m = hashlib.sha256()
    m.update(open(fname, 'rb').read())
    with open(hashname, 'w', encoding='utf-8') as f:
        # A space and an asterisk because that is the format defined by GNU coreutils
        # and accepted by busybox and the Perl shasum tool.
        f.write('{} *{}\n'.format(m.hexdigest(), os.path.basename(fname)))


def copy_git(src, distdir, revision='HEAD', prefix=None, subdir=None):
    cmd = ['git', 'archive', '--format', 'tar', revision]
    if prefix is not None:
        cmd.insert(2, f'--prefix={prefix}/')
    if subdir is not None:
        cmd.extend(['--', subdir])
    with tempfile.TemporaryFile() as f:
        subprocess.check_call(cmd, cwd=src, stdout=f)
        f.seek(0)
        t = tarfile.open(fileobj=f) # [ignore encoding]
        t.extractall(path=distdir)

def process_submodules(src, distdir):
    module_file = os.path.join(src, '.gitmodules')
    if not os.path.exists(module_file):
        return
    cmd = ['git', 'submodule', 'status', '--cached', '--recursive']
    modlist = subprocess.check_output(cmd, cwd=src, universal_newlines=True).splitlines()
    for submodule in modlist:
        status = submodule[:1]
        sha1, rest = submodule[1:].split(' ', 1)
        subpath = rest.rsplit(' ', 1)[0]

        if status == '-':
            mlog.warning(f'Submodule {subpath!r} is not checked out and cannot be added to the dist')
            continue
        elif status in {'+', 'U'}:
            mlog.warning(f'Submodule {subpath!r} has uncommitted changes that will not be included in the dist tarball')

        copy_git(os.path.join(src, subpath), distdir, revision=sha1, prefix=subpath)


def run_dist_scripts(src_root, bld_root, dist_root, dist_scripts, subprojects):
    assert os.path.isabs(dist_root)
    env = {}
    env['MESON_DIST_ROOT'] = dist_root
    env['MESON_SOURCE_ROOT'] = src_root
    env['MESON_BUILD_ROOT'] = bld_root
    for d in dist_scripts:
        if d.subproject and d.subproject not in subprojects:
            continue
        subdir = subprojects.get(d.subproject, '')
        env['MESON_PROJECT_DIST_ROOT'] = os.path.join(dist_root, subdir)
        env['MESON_PROJECT_SOURCE_ROOT'] = os.path.join(src_root, subdir)
        env['MESON_PROJECT_BUILD_ROOT'] = os.path.join(bld_root, subdir)
        name = ' '.join(d.cmd_args)
        print(f'Running custom dist script {name!r}')
        try:
            rc = run_exe(d, env)
            if rc != 0:
                sys.exit('Dist script errored out')
        except OSError:
            print(f'Failed to run dist script {name!r}')
            sys.exit(1)

def git_root(src_root):
    # Cannot use --show-toplevel here because git in our CI prints cygwin paths
    # that python cannot resolve. Workaround this by taking parent of src_root.
    prefix = quiet_git(['rev-parse', '--show-prefix'], src_root, check=True)[1].strip()
    if not prefix:
        return Path(src_root)
    prefix_level = len(Path(prefix).parents)
    return Path(src_root).parents[prefix_level - 1]

def is_git(src_root):
    '''
    Checks if meson.build file at the root source directory is tracked by git.
    It could be a subproject part of the parent project git repository.
    '''
    return quiet_git(['ls-files', '--error-unmatch', 'meson.build'], src_root)[0]

def git_have_dirty_index(src_root):
    '''Check whether there are uncommitted changes in git'''
    ret = subprocess.call(['git', '-C', src_root, 'diff-index', '--quiet', 'HEAD'])
    return ret == 1

def process_git_project(src_root, distdir):
    if git_have_dirty_index(src_root):
        mlog.warning('Repository has uncommitted changes that will not be included in the dist tarball')
    if os.path.exists(distdir):
        windows_proof_rmtree(distdir)
    repo_root = git_root(src_root)
    if repo_root.samefile(src_root):
        os.makedirs(distdir)
        copy_git(src_root, distdir)
    else:
        subdir = Path(src_root).relative_to(repo_root)
        tmp_distdir = distdir + '-tmp'
        if os.path.exists(tmp_distdir):
            windows_proof_rmtree(tmp_distdir)
        os.makedirs(tmp_distdir)
        copy_git(repo_root, tmp_distdir, subdir=str(subdir))
        Path(tmp_distdir, subdir).rename(distdir)
        windows_proof_rmtree(tmp_distdir)
    process_submodules(src_root, distdir)

def create_dist_git(dist_name, archives, src_root, bld_root, dist_sub, dist_scripts, subprojects):
    distdir = os.path.join(dist_sub, dist_name)
    process_git_project(src_root, distdir)
    for path in subprojects.values():
        sub_src_root = os.path.join(src_root, path)
        sub_distdir = os.path.join(distdir, path)
        if os.path.exists(sub_distdir):
            continue
        if is_git(sub_src_root):
            process_git_project(sub_src_root, sub_distdir)
        else:
            shutil.copytree(sub_src_root, sub_distdir)
    run_dist_scripts(src_root, bld_root, distdir, dist_scripts, subprojects)
    output_names = []
    for a in archives:
        compressed_name = distdir + archive_extension[a]
        shutil.make_archive(distdir, a, root_dir=dist_sub, base_dir=dist_name)
        output_names.append(compressed_name)
    windows_proof_rmtree(distdir)
    return output_names

def is_hg(src_root):
    return os.path.isdir(os.path.join(src_root, '.hg'))

def hg_have_dirty_index(src_root):
    '''Check whether there are uncommitted changes in hg'''
    out = subprocess.check_output(['hg', '-R', src_root, 'summary'])
    return b'commit: (clean)' not in out

def create_dist_hg(dist_name, archives, src_root, bld_root, dist_sub, dist_scripts):
    if hg_have_dirty_index(src_root):
        mlog.warning('Repository has uncommitted changes that will not be included in the dist tarball')
    if dist_scripts:
        mlog.warning('dist scripts are not supported in Mercurial projects')

    os.makedirs(dist_sub, exist_ok=True)
    tarname = os.path.join(dist_sub, dist_name + '.tar')
    xzname = tarname + '.xz'
    gzname = tarname + '.gz'
    zipname = os.path.join(dist_sub, dist_name + '.zip')
    # Note that -X interprets relative paths using the current working
    # directory, not the repository root, so this must be an absolute path:
    # https://bz.mercurial-scm.org/show_bug.cgi?id=6267
    #
    # .hg[a-z]* is used instead of .hg* to keep .hg_archival.txt, which may
    # be useful to link the tarball to the Mercurial revision for either
    # manual inspection or in case any code interprets it for a --version or
    # similar.
    subprocess.check_call(['hg', 'archive', '-R', src_root, '-S', '-t', 'tar',
                           '-X', src_root + '/.hg[a-z]*', tarname])
    output_names = []
    if 'xztar' in archives:
        import lzma
        with lzma.open(xzname, 'wb') as xf, open(tarname, 'rb') as tf:
            shutil.copyfileobj(tf, xf)
        output_names.append(xzname)
    if 'gztar' in archives:
        with gzip.open(gzname, 'wb') as zf, open(tarname, 'rb') as tf:
            shutil.copyfileobj(tf, zf)
        output_names.append(gzname)
    os.unlink(tarname)
    if 'zip' in archives:
        subprocess.check_call(['hg', 'archive', '-R', src_root, '-S', '-t', 'zip', zipname])
        output_names.append(zipname)
    return output_names

def run_dist_steps(meson_command, unpacked_src_dir, builddir, installdir, ninja_args):
    if subprocess.call(meson_command + ['--backend=ninja', unpacked_src_dir, builddir]) != 0:
        print('Running Meson on distribution package failed')
        return 1
    if subprocess.call(ninja_args, cwd=builddir) != 0:
        print('Compiling the distribution package failed')
        return 1
    if subprocess.call(ninja_args + ['test'], cwd=builddir) != 0:
        print('Running unit tests on the distribution package failed')
        return 1
    myenv = os.environ.copy()
    myenv['DESTDIR'] = installdir
    if subprocess.call(ninja_args + ['install'], cwd=builddir, env=myenv) != 0:
        print('Installing the distribution package failed')
        return 1
    return 0

def check_dist(packagename, meson_command, extra_meson_args, bld_root, privdir):
    print(f'Testing distribution package {packagename}')
    unpackdir = os.path.join(privdir, 'dist-unpack')
    builddir = os.path.join(privdir, 'dist-build')
    installdir = os.path.join(privdir, 'dist-install')
    for p in (unpackdir, builddir, installdir):
        if os.path.exists(p):
            windows_proof_rmtree(p)
        os.mkdir(p)
    ninja_args = detect_ninja()
    shutil.unpack_archive(packagename, unpackdir)
    unpacked_files = glob(os.path.join(unpackdir, '*'))
    assert len(unpacked_files) == 1
    unpacked_src_dir = unpacked_files[0]
    with open(os.path.join(bld_root, 'meson-info', 'intro-buildoptions.json'), encoding='utf-8') as boptions:
        meson_command += ['-D{name}={value}'.format(**o) for o in json.load(boptions)
                          if o['name'] not in ['backend', 'install_umask', 'buildtype']]
    meson_command += extra_meson_args

    ret = run_dist_steps(meson_command, unpacked_src_dir, builddir, installdir, ninja_args)
    if ret > 0:
        print(f'Dist check build directory was {builddir}')
    else:
        windows_proof_rmtree(unpackdir)
        windows_proof_rmtree(builddir)
        windows_proof_rmtree(installdir)
        print(f'Distribution package {packagename} tested')
    return ret

def determine_archives_to_generate(options):
    result = []
    for i in options.formats.split(','):
        if i not in archive_choices:
            sys.exit(f'Value "{i}" not one of permitted values {archive_choices}.')
        result.append(i)
    if len(i) == 0:
        sys.exit('No archive types specified.')
    return result

def run(options):
    buildfile = Path(options.wd) / 'meson-private' / 'build.dat'
    if not buildfile.is_file():
        raise MesonException(f'Directory {options.wd!r} does not seem to be a Meson build directory.')
    b = build.load(options.wd)
    setup_vsenv(b.need_vsenv)
    # This import must be load delayed, otherwise it will get the default
    # value of None.
    from mesonbuild.mesonlib import get_meson_command
    src_root = b.environment.source_dir
    bld_root = b.environment.build_dir
    priv_dir = os.path.join(bld_root, 'meson-private')
    dist_sub = os.path.join(bld_root, 'meson-dist')

    dist_name = b.project_name + '-' + b.project_version

    archives = determine_archives_to_generate(options)

    subprojects = {}
    extra_meson_args = []
    if options.include_subprojects:
        subproject_dir = os.path.join(src_root, b.subproject_dir)
        for sub in b.subprojects:
            directory = wrap.get_directory(subproject_dir, sub)
            subprojects[sub] = os.path.join(b.subproject_dir, directory)
        extra_meson_args.append('-Dwrap_mode=nodownload')

    if is_git(src_root):
        names = create_dist_git(dist_name, archives, src_root, bld_root, dist_sub, b.dist_scripts, subprojects)
    elif is_hg(src_root):
        if subprojects:
            print('--include-subprojects option currently not supported with Mercurial')
            return 1
        names = create_dist_hg(dist_name, archives, src_root, bld_root, dist_sub, b.dist_scripts)
    else:
        print('Dist currently only works with Git or Mercurial repos')
        return 1
    if names is None:
        return 1
    rc = 0
    if not options.no_tests:
        # Check only one.
        rc = check_dist(names[0], get_meson_command(), extra_meson_args, bld_root, priv_dir)
    if rc == 0:
        for name in names:
            create_hash(name)
            print('Created', name)
    return rc
