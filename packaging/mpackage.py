#!/usr/bin/env python3

# Converts a release tarball to a Debian package.

# This script only works on Jussi's private release machine.

import os, sys, subprocess, re, shutil
import tarfile
from glob import glob
import pathlib

assert(os.getcwd() == '/home/jpakkane')

packdir = 'mesonpackaging'
relfile = packdir + '/releases'

files = glob('meson/dist/*.tar.gz')
assert(len(files) == 1)
infile = files[0]

with tarfile.open(infile , 'r') as tf:
    for e in tf.getmembers():
        if '__pycache__' in e.name or e.name.endswith('.pyc'):
            sys.exit('Source archive has Python binary files:' + str(e.name))

fname = os.path.split(infile)[1]
tmp = fname.replace('-', '_')

assert fname.endswith('.tar.gz')
version_part = fname.split('-', 1)[1][:-7]

if 'rc' in version_part:
    base_version, rcnum = version_part.split('rc')
    version = base_version + 'rc' + rcnum
    extension = tmp[-7:]
    dchversion = base_version + '~rc' + rcnum
    origname = tmp.split('rc', 1)[0] + '~rc' + rcnum + '.orig' + extension
else:
    origname = tmp[:-7] + '.orig.' + tmp[-6:]
    version = version_part
    dchversion = version
version_lines = pathlib.Path(relfile).read_text().split('\n')[:-1]
prev_ver = version_lines[-1]
version_lines.append(version)
print('Deb orig name is', origname)
print('Version is', version)
print('Previous version is', prev_ver)
assert(prev_ver)
outdir = os.path.join(packdir, version)
origfile = os.path.join(packdir, version, origname)
if not os.path.exists(outdir):
    os.mkdir(outdir)
    shutil.copyfile(infile, origfile)
    subprocess.check_call(['tar', 'xf', origname], cwd=outdir)
    extractdir = glob(os.path.join(packdir, version, 'meson-*'))[0]
    fromdeb = glob(os.path.join(packdir, prev_ver, 'meson-*/debian'))[0]
    todeb = os.path.join(extractdir, 'debian')
    shutil.copytree(fromdeb, todeb)
    myenv = os.environ.copy()
    myenv['EDITOR'] = 'emacs'
    subprocess.check_call(['dch', '-v', dchversion + '-1'], cwd=extractdir, env=myenv)
    pathlib.Path(relfile).write_text('\n'.join(version_lines) + '\n')
else:
    extractdir = glob(os.path.join(packdir, version, 'meson-*'))[0]
    print('Outdir already exists')

subprocess.check_call(['debuild', '-S'], cwd=extractdir)

subprocess.call(['sudo rm -rf /var/cache/pbuilder/result/*'], shell=True)
subprocess.check_call('sudo pbuilder --build *.dsc 2>&1 | tee buildlog.txt',
                      shell=True,
                      cwd=outdir)
subprocess.check_call('sudo dpkg -i /var/cache/pbuilder/result/meson*all.deb',
                      shell=True)

if os.path.exists('smoke/build'):
    shutil.rmtree('smoke/build')
if os.path.exists('smoke/buildcross'):
    shutil.rmtree('smoke/buildcross')
subprocess.check_call(['meson', 'setup', 'build'], cwd='smoke')
subprocess.check_call(['ninja', 'test'], cwd='smoke/build')
subprocess.check_call(['ninja', 'reconfigure'], cwd='smoke/build')
subprocess.check_call(['ninja', 'test'], cwd='smoke/build')
#subprocess.check_call(['/usr/bin/meson',
#                       'env2mfile',
#                       '--cross',
#                       '--debarch',
#                       'armhf',
#                       '-o',
#                       'cross-file.txt'], cwd='smoke')
subprocess.check_call(['/usr/share/meson/debcrossgen',
                       '--arch',
                       'armhf',
                       '-o',
                       'cross-file.txt'], cwd='smoke')
subprocess.check_call(['meson',
                       'setup',
                       'buildcross',
                       '--cross-file',
                       'cross-file.txt'], cwd='smoke')
subprocess.check_call(['ninja', 'test'], cwd='smoke/buildcross')
subprocess.check_call(['sudo', 'apt-get', '-y', 'remove', 'meson'])
subprocess.call('rm meson-*tar.gz*', shell=True)
subprocess.check_call(['cp', infile, '.'])
subprocess.check_call(['gpg', '--detach-sign', '--armor', fname])
