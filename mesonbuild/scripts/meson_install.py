#!/usr/bin/env python3

# Copyright 2013-2014 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, pickle, os, shutil, subprocess, gzip, platform
from glob import glob
from mesonbuild.scripts import depfixer

def do_install(datafilename):
    ifile = open(datafilename, 'rb')
    d = pickle.load(ifile)
    destdir_var = 'DESTDIR'
    if destdir_var in os.environ:
        d.destdir = os.environ[destdir_var]
    else:
        d.destdir = ''
    d.fullprefix = d.destdir + d.prefix

    install_subdirs(d) # Must be first, because it needs to delete the old subtree.
    install_targets(d)
    install_headers(d)
    install_man(d)
    install_data(d)
    install_po(d)
    run_install_script(d)

def install_subdirs(d):
    for (src_dir, dst_dir) in d.install_subdirs:
        if os.path.isabs(dst_dir):
            dst_dir = d.destdir + dst_dir
        else:
            dst_dir = d.fullprefix + dst_dir
        # Python's copytree works in strange ways.
        last_level = os.path.split(src_dir)[-1]
        final_dst = os.path.join(dst_dir, last_level)
# Don't do rmtree because final_dst might point to e.g. /var/www
# We might need to revert to walking the directory tree by hand.
#        shutil.rmtree(final_dst, ignore_errors=True)
        shutil.copytree(src_dir, final_dst, symlinks=True)
        print('Installing subdir %s to %s.' % (src_dir, dst_dir))

def install_po(d):
    packagename = d.po_package_name
    for f in d.po:
        srcfile = f[0]
        localedir = f[1]
        languagename = f[2]
        outfile = os.path.join(d.fullprefix, localedir, languagename, 'LC_MESSAGES',
                               packagename + '.mo')
        os.makedirs(os.path.split(outfile)[0], exist_ok=True)
        shutil.copyfile(srcfile, outfile)
        shutil.copystat(srcfile, outfile)
        print('Installing %s to %s.' % (srcfile, outfile))

def install_data(d):
    for i in d.data:
        fullfilename = i[0]
        outfilename = i[1]
        if os.path.isabs(outfilename):
            outdir = d.destdir + os.path.split(outfilename)[0]
            outfilename = d.destdir + outfilename
        else:
            outdir = os.path.join(d.fullprefix, os.path.split(outfilename)[0])
            outfilename = os.path.join(outdir, os.path.split(outfilename)[1])
        os.makedirs(outdir, exist_ok=True)
        print('Installing %s to %s.' % (fullfilename, outdir))
        shutil.copyfile(fullfilename, outfilename)
        shutil.copystat(fullfilename, outfilename)

def install_man(d):
    for m in d.man:
        outfileroot = m[1]
        outfilename = os.path.join(d.fullprefix, outfileroot)
        full_source_filename = m[0]
        outdir = os.path.split(outfilename)[0]
        os.makedirs(outdir, exist_ok=True)
        print('Installing %s to %s.' % (full_source_filename, outdir))
        if outfilename.endswith('.gz') and not full_source_filename.endswith('.gz'):
            open(outfilename, 'wb').write(gzip.compress(open(full_source_filename, 'rb').read()))
        else:
            shutil.copyfile(full_source_filename, outfilename)
        shutil.copystat(full_source_filename, outfilename)

def install_headers(d):
    for t in d.headers:
        fullfilename = t[0]
        outdir = os.path.join(d.fullprefix, t[1])
        fname = os.path.split(fullfilename)[1]
        outfilename = os.path.join(outdir, fname)
        print('Installing %s to %s' % (fname, outdir))
        os.makedirs(outdir, exist_ok=True)
        shutil.copyfile(fullfilename, outfilename)
        shutil.copystat(fullfilename, outfilename)

def run_install_script(d):
    env = {'MESON_SOURCE_ROOT' : d.source_dir,
           'MESON_BUILD_ROOT' : d.build_dir,
           'MESON_INSTALL_PREFIX' : d.prefix
          }
    child_env = os.environ.copy()
    child_env.update(env)

    for i in d.install_scripts:
        script = i.cmd_arr[0]
        print('Running custom install script %s' % script)
        suffix = os.path.splitext(script)[1].lower()
        if platform.system().lower() == 'windows' and suffix != '.bat':
            first_line = open(script).readline().strip()
            if first_line.startswith('#!'):
                if shutil.which(first_line[2:]):
                    commands = [first_line[2:]]
                else:
                    commands = first_line[2:].split('#')[0].strip().split()
                    commands[0] = shutil.which(commands[0].split('/')[-1])
                    if commands[0] is None:
                        commands
                        raise RuntimeError("Don't know how to run script %s." % script)
                final_command = commands + [script] + i.cmd_arr[1:]
        else:
            final_command = i.cmd_arr
        try:
            rc = subprocess.call(final_command, env=child_env)
            if rc != 0:
                sys.exit(rc)
        except:
            print('Failed to run install script:', *i.cmd_arr)
            sys.exit(1)

def is_elf_platform():
    platname = platform.system().lower()
    if platname == 'darwin' or platname == 'windows':
        return False
    return True

def check_for_stampfile(fname):
    '''Some languages e.g. Rust have output files
    whose names are not known at configure time.
    Check if this is the case and return the real
    file instead.'''
    if fname.endswith('.so') or fname.endswith('.dll'):
        if os.stat(fname).st_size == 0:
            (base, suffix) = os.path.splitext(fname)
            files = glob(base + '-*' + suffix)
            if len(files) > 1:
                print("Stale dynamic library files in build dir. Can't install.")
                sys.exit(1)
            if len(files) == 1:
                return files[0]
    elif fname.endswith('.a') or fname.endswith('.lib'):
        if os.stat(fname).st_size == 0:
            (base, suffix) = os.path.splitext(fname)
            files = glob(base + '-*' + '.rlib')
            if len(files) > 1:
                print("Stale static library files in build dir. Can't install.")
                sys.exit(1)
            if len(files) == 1:
                return files[0]
    return fname

def install_targets(d):
    for t in d.targets:
        fname = check_for_stampfile(t[0])
        outdir = os.path.join(d.fullprefix, t[1])
        aliases = t[2]
        outname = os.path.join(outdir, os.path.split(fname)[-1])
        should_strip = t[3]
        install_rpath = t[4]
        print('Installing %s to %s' % (fname, outname))
        os.makedirs(outdir, exist_ok=True)
        shutil.copyfile(fname, outname)
        shutil.copystat(fname, outname)
        if should_strip:
            print('Stripping target')
            ps = subprocess.Popen(['strip', outname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdo, stde) = ps.communicate()
            if ps.returncode != 0:
                print('Could not strip file.\n')
                print('Stdout:\n%s\n' % stdo.decode())
                print('Stderr:\n%s\n' % stde.decode())
                sys.exit(1)
        printed_symlink_error = False
        for alias in aliases:
            try:
                symlinkfilename = os.path.join(outdir, alias)
                try:
                    os.unlink(symlinkfilename)
                except FileNotFoundError:
                    pass
                os.symlink(os.path.split(fname)[-1], symlinkfilename)
            except (NotImplementedError, OSError):
                if not printed_symlink_error:
                    print("Symlink creation does not work on this platform.")
                    printed_symlink_error = True
        if is_elf_platform():
            try:
                e = depfixer.Elf(outname, False)
                e.fix_rpath(install_rpath)
            except SystemExit as e:
                if isinstance(e.code, int) and e.code == 0:
                    pass
                else:
                    raise

def run(args):
    if len(args) != 1:
        print('Installer script for Meson. Do not run on your own, mmm\'kay?')
        print('meson_install.py [install info file]')
    datafilename = args[0]
    do_install(datafilename)
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
