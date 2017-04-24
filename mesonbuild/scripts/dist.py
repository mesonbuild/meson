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


import os, sys
import shutil
import argparse
import subprocess
import pickle
import hashlib
import tarfile, zipfile
import tempfile
from glob import glob
from mesonbuild.environment import detect_ninja

def create_hash(fname):
    hashname = fname + '.sha256sum'
    m = hashlib.sha256()
    m.update(open(fname, 'rb').read())
    with open(hashname, 'w') as f:
        f.write('%s %s\n' % (m.hexdigest(), os.path.split(fname)[-1]))

def create_zip(zipfilename, packaging_dir):
    prefix = os.path.split(packaging_dir)[0]
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

def create_dist(dist_name, src_root, bld_root, dist_sub):
    distdir = os.path.join(dist_sub, dist_name)
    gitdir = os.path.join(src_root, '.git')
    if os.path.exists(distdir):
        shutil.rmtree(distdir)
    os.makedirs(distdir)
    dest_gitdir = os.path.join(distdir, '.git')
    shutil.copytree(gitdir, dest_gitdir)
    subprocess.check_call(['git', 'reset', '--hard'], cwd=distdir)
    shutil.rmtree(dest_gitdir)
    for f in glob(os.path.join(distdir, '.git*')):
        os.unlink(f)
    xzname = distdir + '.tar.xz'
    zipname = distdir + '.zip'
    # Should use shutil but it got xz support only in 3.5.
    with tarfile.open(xzname, 'w:xz') as tf:
        tf.add(distdir, os.path.split(distdir)[1])
    create_zip(zipname, distdir)
    shutil.rmtree(distdir)
    return (xzname, zipname)

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
        if subprocess.call(meson_command + [srcdir, builddir]) != 0:
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
        shutil.rmtree(srcdir)
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

    if not os.path.isdir(os.path.join(src_root, '.git')):
        print('Dist currently only works with Git repos.')
        return 1
    names = create_dist(dist_name, src_root, bld_root, dist_sub)
    if names is None:
        return 1
    rc = check_dist(names[0], meson_command) # Check only one.
    if rc == 0:
        # Only create the hash if the build is successfull.
        for n in names:
            create_hash(n)
    return rc
