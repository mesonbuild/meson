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

import sys, pickle, os, shutil, subprocess, gzip, platform, errno
from glob import glob
from . import depfixer
from . import destdir_join
from ..mesonlib import is_windows, Popen_safe

install_log_file = None

def set_mode(path, mode):
    if mode is None:
        # Keep mode unchanged
        return
    if (mode.perms_s or mode.owner or mode.group) is None:
        # Nothing to set
        return
    # No chown() on Windows, and must set one of owner/group
    if not is_windows() and (mode.owner or mode.group) is not None:
        try:
            shutil.chown(path, mode.owner, mode.group)
        except PermissionError as e:
            msg = '{!r}: Unable to set owner {!r} and group {!r}: {}, ignoring...'
            print(msg.format(path, mode.owner, mode.group, e.strerror))
        except LookupError:
            msg = '{!r}: Non-existent owner {!r} or group {!r}: ignoring...'
            print(msg.format(path, mode.owner, mode.group))
        except OSError as e:
            if e.errno == errno.EINVAL:
                msg = '{!r}: Non-existent numeric owner {!r} or group {!r}: ignoring...'
                print(msg.format(path, mode.owner, mode.group))
            else:
                raise
    # Must set permissions *after* setting owner/group otherwise the
    # setuid/setgid bits will get wiped by chmod
    # NOTE: On Windows you can set read/write perms; the rest are ignored
    if mode.perms_s is not None:
        try:
            os.chmod(path, mode.perms)
        except PermissionError as e:
            msg = '{!r}: Unable to set permissions {!r}: {}, ignoring...'
            print(msg.format(path, mode.perms_s, e.strerror))

def append_to_log(line):
    install_log_file.write(line)
    if not line.endswith('\n'):
        install_log_file.write('\n')
    install_log_file.flush()

def do_copyfile(from_file, to_file):
    if not os.path.isfile(from_file):
        raise RuntimeError('Tried to install something that isn\'t a file:'
                           '{!r}'.format(from_file))
    # copyfile fails if the target file already exists, so remove it to
    # allow overwriting a previous install. If the target is not a file, we
    # want to give a readable error.
    if os.path.exists(to_file):
        if not os.path.isfile(to_file):
            raise RuntimeError('Destination {!r} already exists and is not '
                               'a file'.format(to_file))
        os.unlink(to_file)
    shutil.copyfile(from_file, to_file)
    shutil.copystat(from_file, to_file)
    append_to_log(to_file)

def do_copydir(src_prefix, src_dir, dst_dir):
    '''
    Copies the directory @src_prefix (full path) into @dst_dir

    @src_dir is simply the parent directory of @src_prefix
    '''
    for root, dirs, files in os.walk(src_prefix):
        for d in dirs:
            abs_src = os.path.join(src_dir, root, d)
            filepart = abs_src[len(src_dir) + 1:]
            abs_dst = os.path.join(dst_dir, filepart)
            if os.path.isdir(abs_dst):
                continue
            if os.path.exists(abs_dst):
                print('Tried to copy directory %s but a file of that name already exists.' % abs_dst)
                sys.exit(1)
            os.makedirs(abs_dst)
            shutil.copystat(abs_src, abs_dst)
        for f in files:
            abs_src = os.path.join(src_dir, root, f)
            filepart = abs_src[len(src_dir) + 1:]
            abs_dst = os.path.join(dst_dir, filepart)
            if os.path.isdir(abs_dst):
                print('Tried to copy file %s but a directory of that name already exists.' % abs_dst)
            if os.path.exists(abs_dst):
                os.unlink(abs_dst)
            parent_dir = os.path.split(abs_dst)[0]
            if not os.path.isdir(parent_dir):
                os.mkdir(parent_dir)
                shutil.copystat(os.path.split(abs_src)[0], parent_dir)
            shutil.copy2(abs_src, abs_dst, follow_symlinks=False)
            append_to_log(abs_dst)

def get_destdir_path(d, path):
    if os.path.isabs(path):
        output = destdir_join(d.destdir, path)
    else:
        output = os.path.join(d.fullprefix, path)
    return output

def do_install(datafilename):
    with open(datafilename, 'rb') as ifile:
        d = pickle.load(ifile)
    d.destdir = os.environ.get('DESTDIR', '')
    d.fullprefix = destdir_join(d.destdir, d.prefix)

    install_subdirs(d) # Must be first, because it needs to delete the old subtree.
    install_targets(d)
    install_headers(d)
    install_man(d)
    install_data(d)
    run_install_script(d)

def install_subdirs(data):
    for (src_dir, inst_dir, dst_dir, mode) in data.install_subdirs:
        if src_dir.endswith('/') or src_dir.endswith('\\'):
            src_dir = src_dir[:-1]
        src_prefix = os.path.join(src_dir, inst_dir)
        print('Installing subdir %s to %s' % (src_prefix, dst_dir))
        dst_dir = get_destdir_path(data, dst_dir)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        do_copydir(src_prefix, src_dir, dst_dir)
        dst_prefix = os.path.join(dst_dir, inst_dir)
        set_mode(dst_prefix, mode)

def install_data(d):
    for i in d.data:
        fullfilename = i[0]
        outfilename = get_destdir_path(d, i[1])
        mode = i[2]
        outdir = os.path.split(outfilename)[0]
        os.makedirs(outdir, exist_ok=True)
        print('Installing %s to %s' % (fullfilename, outdir))
        do_copyfile(fullfilename, outfilename)
        set_mode(outfilename, mode)

def install_man(d):
    for m in d.man:
        full_source_filename = m[0]
        outfilename = get_destdir_path(d, m[1])
        outdir = os.path.split(outfilename)[0]
        os.makedirs(outdir, exist_ok=True)
        print('Installing %s to %s' % (full_source_filename, outdir))
        if outfilename.endswith('.gz') and not full_source_filename.endswith('.gz'):
            with open(outfilename, 'wb') as of:
                with open(full_source_filename, 'rb') as sf:
                    of.write(gzip.compress(sf.read()))
            shutil.copystat(full_source_filename, outfilename)
            append_to_log(outfilename)
        else:
            do_copyfile(full_source_filename, outfilename)

def install_headers(d):
    for t in d.headers:
        fullfilename = t[0]
        fname = os.path.split(fullfilename)[1]
        outdir = get_destdir_path(d, t[1])
        outfilename = os.path.join(outdir, fname)
        print('Installing %s to %s' % (fname, outdir))
        os.makedirs(outdir, exist_ok=True)
        do_copyfile(fullfilename, outfilename)

def run_install_script(d):
    env = {'MESON_SOURCE_ROOT': d.source_dir,
           'MESON_BUILD_ROOT': d.build_dir,
           'MESON_INSTALL_PREFIX': d.prefix,
           'MESON_INSTALL_DESTDIR_PREFIX': d.fullprefix,
           'MESONINTROSPECT': d.mesonintrospect}
    child_env = os.environ.copy()
    child_env.update(env)

    for i in d.install_scripts:
        script = i['exe']
        args = i['args']
        name = ' '.join(script + args)
        print('Running custom install script {!r}'.format(name))
        try:
            rc = subprocess.call(script + args, env=child_env)
            if rc != 0:
                sys.exit(rc)
        except:
            print('Failed to run install script {!r}'.format(name))
            sys.exit(1)

def is_elf_platform():
    platname = platform.system().lower()
    if platname == 'darwin' or platname == 'windows' or platname == 'cygwin':
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
        outdir = get_destdir_path(d, t[1])
        outname = os.path.join(outdir, os.path.split(fname)[-1])
        aliases = t[2]
        should_strip = t[3]
        install_rpath = t[4]
        print('Installing %s to %s' % (fname, outname))
        os.makedirs(outdir, exist_ok=True)
        if not os.path.exists(fname):
            raise RuntimeError('File {!r} could not be found'.format(fname))
        elif os.path.isfile(fname):
            do_copyfile(fname, outname)
            if should_strip and d.strip_bin is not None:
                if fname.endswith('.jar'):
                    print('Not stripping jar target:', os.path.split(fname)[1])
                    continue
                print('Stripping target {!r}'.format(fname))
                ps, stdo, stde = Popen_safe(d.strip_bin + [outname])
                if ps.returncode != 0:
                    print('Could not strip file.\n')
                    print('Stdout:\n%s\n' % stdo)
                    print('Stderr:\n%s\n' % stde)
                    sys.exit(1)
            pdb_filename = os.path.splitext(fname)[0] + '.pdb'
            if not should_strip and os.path.exists(pdb_filename):
                pdb_outname = os.path.splitext(outname)[0] + '.pdb'
                print('Installing pdb file %s to %s' % (pdb_filename, pdb_outname))
                do_copyfile(pdb_filename, pdb_outname)
        elif os.path.isdir(fname):
            fname = os.path.join(d.build_dir, fname.rstrip('/'))
            do_copydir(fname, os.path.dirname(fname), outdir)
        else:
            raise RuntimeError('Unknown file type for {!r}'.format(fname))
        printed_symlink_error = False
        for alias, to in aliases.items():
            try:
                symlinkfilename = os.path.join(outdir, alias)
                try:
                    os.unlink(symlinkfilename)
                except FileNotFoundError:
                    pass
                os.symlink(to, symlinkfilename)
                append_to_log(symlinkfilename)
            except (NotImplementedError, OSError):
                if not printed_symlink_error:
                    print("Symlink creation does not work on this platform. "
                          "Skipping all symlinking.")
                    printed_symlink_error = True
        if is_elf_platform() and os.path.isfile(outname):
            try:
                e = depfixer.Elf(outname, False)
                e.fix_rpath(install_rpath)
            except SystemExit as e:
                if isinstance(e.code, int) and e.code == 0:
                    pass
                else:
                    raise

def run(args):
    global install_log_file
    if len(args) != 1:
        print('Installer script for Meson. Do not run on your own, mmm\'kay?')
        print('meson_install.py [install info file]')
    datafilename = args[0]
    private_dir = os.path.split(datafilename)[0]
    log_dir = os.path.join(private_dir, '../meson-logs')
    with open(os.path.join(log_dir, 'install-log.txt'), 'w') as lf:
        install_log_file = lf
        append_to_log('# List of files installed by Meson')
        append_to_log('# Does not contain files installed by custom scripts.')
        do_install(datafilename)
    install_log_file = None
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
