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


import lzma
import os
import sys
import shutil
import subprocess
import pickle
import hashlib
import tarfile, zipfile
import tempfile
from glob import glob
from mesonbuild.environment import detect_ninja
from mesonbuild.dependencies import ExternalProgram
from mesonbuild.mesonlib import windows_proof_rmtree

def create_hash(fname):
    hashname = fname + '.sha256sum'
    m = hashlib.sha256()
    m.update(open(fname, 'rb').read())
    with open(hashname, 'w') as f:
        f.write('%s %s\n' % (m.hexdigest(), os.path.basename(fname)))


def create_zip(zipfilename, packaging_dir):
    prefix = os.path.dirname(packaging_dir)
    removelen = len(prefix) + 1
    with zipfile.ZipFile(zipfilename,
                         'w',
                         compression=zipfile.ZIP_DEFLATED,
                         allowZip64=True) as zf:
        zf.write(packaging_dir, packaging_dir[removelen:])
        for root, dirs, files in os.walk(packaging_dir):
            for d in dirs:
                dname = os.path.join(root, d)
                zf.write(dname, dname[removelen:])
            for f in files:
                fname = os.path.join(root, f)
                zf.write(fname, fname[removelen:])

def del_gitfiles(dirname):
    for f in glob(os.path.join(dirname, '.git*')):
        if os.path.isdir(f) and not os.path.islink(f):
            windows_proof_rmtree(f)
        else:
            os.unlink(f)

def process_submodules(dirname):
    module_file = os.path.join(dirname, '.gitmodules')
    if not os.path.exists(module_file):
        return
    subprocess.check_call(['git', 'submodule', 'update', '--init'], cwd=dirname)
    for line in open(module_file):
        line = line.strip()
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        v = v.strip()
        if k != 'path':
            continue
        del_gitfiles(os.path.join(dirname, v))


def run_dist_scripts(dist_root, dist_scripts):
    assert(os.path.isabs(dist_root))
    env = os.environ.copy()
    env['MESON_DIST_ROOT'] = dist_root
    for d in dist_scripts:
        print('Processing dist script %s.' % d)
        ddir, dname = os.path.split(d)
        ep = ExternalProgram(dname,
                             search_dir=os.path.join(dist_root, ddir),
                             silent=True)
        if not ep.found():
            sys.exit('Script %s could not be found in dist directory.' % d)
        pc = subprocess.run(ep.command, env=env)
        if pc.returncode != 0:
            sys.exit('Dist script errored out.')

def create_dist_git(dist_name, src_root, bld_root, dist_sub, dist_scripts):
    distdir = os.path.join(dist_sub, dist_name)
    if os.path.exists(distdir):
        shutil.rmtree(distdir)
    os.makedirs(distdir)
    subprocess.check_call(['git', 'clone', '--shared', src_root, distdir])
    process_submodules(distdir)
    del_gitfiles(distdir)
    run_dist_scripts(distdir, dist_scripts)
    xzname = distdir + '.tar.xz'
    # Should use shutil but it got xz support only in 3.5.
    with tarfile.open(xzname, 'w:xz') as tf:
        tf.add(distdir, dist_name)
    # Create only .tar.xz for now.
    # zipname = distdir + '.zip'
    # create_zip(zipname, distdir)
    shutil.rmtree(distdir)
    return (xzname, )


def create_dist_hg(dist_name, src_root, bld_root, dist_sub, dist_scripts):
    os.makedirs(dist_sub, exist_ok=True)

    tarname = os.path.join(dist_sub, dist_name + '.tar')
    xzname = tarname + '.xz'
    subprocess.check_call(['hg', 'archive', '-R', src_root, '-S', '-t', 'tar', tarname])
    if len(dist_scripts) > 0:
        print('WARNING: dist scripts not supported in Mercurial projects.')
    with lzma.open(xzname, 'wb') as xf, open(tarname, 'rb') as tf:
        shutil.copyfileobj(tf, xf)
    os.unlink(tarname)
    # Create only .tar.xz for now.
    # zipname = os.path.join(dist_sub, dist_name + '.zip')
    # subprocess.check_call(['hg', 'archive', '-R', src_root, '-S', '-t', 'zip', zipname])
    return (xzname, )


def check_dist(packagename, meson_command):
    print('Testing distribution package %s.' % packagename)
    unpackdir = tempfile.mkdtemp()
    builddir = tempfile.mkdtemp()
    installdir = tempfile.mkdtemp()
    ninja_bin = detect_ninja()
    try:
        tf = tarfile.open(packagename)
        tf.extractall(unpackdir)
        srcdir = glob(os.path.join(unpackdir, '*'))[0]
        if subprocess.call(meson_command + ['--backend=ninja', srcdir, builddir]) != 0:
            print('Running Meson on distribution package failed')
            return 1
        if subprocess.call([ninja_bin], cwd=builddir) != 0:
            print('Compiling the distribution package failed.')
            return 1
        if subprocess.call([ninja_bin, 'test'], cwd=builddir) != 0:
            print('Running unit tests on the distribution package failed.')
            return 1
        myenv = os.environ.copy()
        myenv['DESTDIR'] = installdir
        if subprocess.call([ninja_bin, 'install'], cwd=builddir, env=myenv) != 0:
            print('Installing the distribution package failed.')
            return 1
    finally:
        shutil.rmtree(unpackdir)
        shutil.rmtree(builddir)
        shutil.rmtree(installdir)
    print('Distribution package %s tested.' % packagename)
    return 0

def run(args):
    src_root = args[0]
    bld_root = args[1]
    meson_command = args[2:]
    priv_dir = os.path.join(bld_root, 'meson-private')
    dist_sub = os.path.join(bld_root, 'meson-dist')

    buildfile = os.path.join(priv_dir, 'build.dat')

    build = pickle.load(open(buildfile, 'rb'))

    dist_name = build.project_name + '-' + build.project_version

    if os.path.isdir(os.path.join(src_root, '.git')):
        names = create_dist_git(dist_name, src_root, bld_root, dist_sub, build.dist_scripts)
    elif os.path.isdir(os.path.join(src_root, '.hg')):
        names = create_dist_hg(dist_name, src_root, bld_root, dist_sub, build.dist_scripts)
    else:
        print('Dist currently only works with Git or Mercurial repos.')
        return 1
    if names is None:
        return 1
    error_count = 0
    for name in names:
        rc = check_dist(name, meson_command) # Check only one.
        if rc == 0:
            create_hash(name)
        error_count += rc
    return 1 if error_count else 0
