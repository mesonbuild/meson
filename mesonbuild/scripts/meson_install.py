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

import sys, pickle, os, shutil, subprocess, gzip, errno
import shlex
from glob import glob
from . import depfixer
from . import destdir_join
from ..mesonlib import is_windows, Popen_safe
from __main__ import __file__ as main_file

install_log_file = None
selinux_updates = []

class DirMaker:
    def __init__(self):
        self.dirs = []

    def makedirs(self, path, exist_ok=False):
        dirname = os.path.normpath(path)
        dirs = []
        while dirname != os.path.dirname(dirname):
            if not os.path.exists(dirname):
                dirs.append(dirname)
            dirname = os.path.dirname(dirname)
        os.makedirs(path, exist_ok=exist_ok)

        # store the directories in creation order, with the parent directory
        # before the child directories. Future calls of makedir() will not
        # create the parent directories, so the last element in the list is
        # the last one to be created. That is the first one to be removed on
        # __exit__
        dirs.reverse()
        self.dirs += dirs

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.dirs.reverse()
        for d in self.dirs:
            append_to_log(d)

def is_executable(path):
    '''Checks whether any of the "x" bits are set in the source file mode.'''
    return bool(os.stat(path).st_mode & 0o111)

def sanitize_permissions(path, umask):
    if umask is None:
        return
    new_perms = 0o777 if is_executable(path) else 0o666
    new_perms &= ~umask
    try:
        os.chmod(path, new_perms)
    except PermissionError as e:
        msg = '{!r}: Unable to set permissions {!r}: {}, ignoring...'
        print(msg.format(path, new_perms, e.strerror))

def set_mode(path, mode, default_umask):
    if mode is None or (mode.perms_s or mode.owner or mode.group) is None:
        # Just sanitize permissions with the default umask
        sanitize_permissions(path, default_umask)
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
    else:
        sanitize_permissions(path, default_umask)

def restore_selinux_contexts():
    '''
    Restores the SELinux context for files in @selinux_updates

    If $DESTDIR is set, do not warn if the call fails.
    '''
    try:
        subprocess.check_call(['selinuxenabled'])
    except (FileNotFoundError, PermissionError, subprocess.CalledProcessError) as e:
        # If we don't have selinux or selinuxenabled returned 1, failure
        # is ignored quietly.
        return

    if not shutil.which('restorecon'):
        # If we don't have restorecon, failure is ignored quietly.
        return

    with subprocess.Popen(['restorecon', '-F', '-f-', '-0'],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        out, err = proc.communicate(input=b'\0'.join(os.fsencode(f) for f in selinux_updates) + b'\0')
        if proc.returncode != 0 and not os.environ.get('DESTDIR'):
            print('Failed to restore SELinux context of installed files...',
                  'Standard output:', out.decode(),
                  'Standard error:', err.decode(), sep='\n')

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
    selinux_updates.append(to_file)
    append_to_log(to_file)

def do_copydir(data, src_dir, dst_dir, exclude, install_mode):
    '''
    Copies the contents of directory @src_dir into @dst_dir.

    For directory
        /foo/
          bar/
            excluded
            foobar
          file
    do_copydir(..., '/foo', '/dst/dir', {'bar/excluded'}, None) creates
        /dst/
          dir/
            bar/
              foobar
            file

    Args:
        src_dir: str, absolute path to the source directory
        dst_dir: str, absolute path to the destination directory
        exclude: (set(str), set(str)), tuple of (exclude_files, exclude_dirs),
                 each element of the set is a path relative to src_dir.
        install_mode: FileMode object, or None to use defaults.
    '''
    if not os.path.isabs(src_dir):
        raise ValueError('src_dir must be absolute, got %s' % src_dir)
    if not os.path.isabs(dst_dir):
        raise ValueError('dst_dir must be absolute, got %s' % dst_dir)
    if exclude is not None:
        exclude_files, exclude_dirs = exclude
    else:
        exclude_files = exclude_dirs = set()
    for root, dirs, files in os.walk(src_dir):
        assert os.path.isabs(root)
        for d in dirs[:]:
            abs_src = os.path.join(root, d)
            filepart = os.path.relpath(abs_src, start=src_dir)
            abs_dst = os.path.join(dst_dir, filepart)
            # Remove these so they aren't visited by os.walk at all.
            if filepart in exclude_dirs:
                dirs.remove(d)
                continue
            if os.path.isdir(abs_dst):
                continue
            if os.path.exists(abs_dst):
                print('Tried to copy directory %s but a file of that name already exists.' % abs_dst)
                sys.exit(1)
            data.dirmaker.makedirs(abs_dst)
            shutil.copystat(abs_src, abs_dst)
            sanitize_permissions(abs_dst, data.install_umask)
        for f in files:
            abs_src = os.path.join(root, f)
            filepart = os.path.relpath(abs_src, start=src_dir)
            if filepart in exclude_files:
                continue
            abs_dst = os.path.join(dst_dir, filepart)
            if os.path.isdir(abs_dst):
                print('Tried to copy file %s but a directory of that name already exists.' % abs_dst)
            if os.path.exists(abs_dst):
                os.unlink(abs_dst)
            parent_dir = os.path.dirname(abs_dst)
            if not os.path.isdir(parent_dir):
                os.mkdir(parent_dir)
                shutil.copystat(os.path.dirname(abs_src), parent_dir)
            shutil.copy2(abs_src, abs_dst, follow_symlinks=False)
            set_mode(abs_dst, install_mode, data.install_umask)
            append_to_log(abs_dst)

def get_destdir_path(d, path):
    if os.path.isabs(path):
        output = destdir_join(d.destdir, path)
    else:
        output = os.path.join(d.fullprefix, path)
    return output

def do_install(log_dir, datafilename):
    global install_log_file

    with open(datafilename, 'rb') as ifile:
        d = pickle.load(ifile)
    d.destdir = os.environ.get('DESTDIR', '')
    d.fullprefix = destdir_join(d.destdir, d.prefix)

    if d.install_umask is not None:
        os.umask(d.install_umask)

    with open(os.path.join(log_dir, 'install-log.txt'), 'w') as lf:
        install_log_file = lf
        append_to_log('# List of files installed by Meson')
        append_to_log('# Does not contain files installed by custom scripts.')

        try:
            d.dirmaker = DirMaker()
            with d.dirmaker:
                install_subdirs(d) # Must be first, because it needs to delete the old subtree.
                install_targets(d)
                install_headers(d)
                install_man(d)
                install_data(d)
                restore_selinux_contexts()
                run_install_script(d)
        except PermissionError:
            if shutil.which('pkexec') is not None and 'PKEXEC_UID' not in os.environ:
                print('Installation failed due to insufficient permissions.')
                print('Attempting to use polkit to gain elevated privileges...')
                os.execlp('pkexec', 'pkexec', sys.executable, main_file, *sys.argv[1:],
                          os.getcwd())
            else:
                raise


def install_subdirs(d):
    for (src_dir, dst_dir, mode, exclude) in d.install_subdirs:
        full_dst_dir = get_destdir_path(d, dst_dir)
        print('Installing subdir %s to %s' % (src_dir, full_dst_dir))
        d.dirmaker.makedirs(full_dst_dir, exist_ok=True)
        do_copydir(d, src_dir, full_dst_dir, exclude, mode)

def install_data(d):
    for i in d.data:
        fullfilename = i[0]
        outfilename = get_destdir_path(d, i[1])
        mode = i[2]
        outdir = os.path.dirname(outfilename)
        d.dirmaker.makedirs(outdir, exist_ok=True)
        print('Installing %s to %s' % (fullfilename, outdir))
        do_copyfile(fullfilename, outfilename)
        set_mode(outfilename, mode, d.install_umask)

def install_man(d):
    for m in d.man:
        full_source_filename = m[0]
        outfilename = get_destdir_path(d, m[1])
        outdir = os.path.dirname(outfilename)
        d.dirmaker.makedirs(outdir, exist_ok=True)
        install_mode = m[2]
        print('Installing %s to %s' % (full_source_filename, outdir))
        if outfilename.endswith('.gz') and not full_source_filename.endswith('.gz'):
            with open(outfilename, 'wb') as of:
                with open(full_source_filename, 'rb') as sf:
                    # Set mtime and filename for reproducibility.
                    with gzip.GzipFile(fileobj=of, mode='wb', filename='', mtime=0) as gz:
                        gz.write(sf.read())
            shutil.copystat(full_source_filename, outfilename)
            append_to_log(outfilename)
        else:
            do_copyfile(full_source_filename, outfilename)
        set_mode(outfilename, install_mode, d.install_umask)

def install_headers(d):
    for t in d.headers:
        fullfilename = t[0]
        fname = os.path.basename(fullfilename)
        outdir = get_destdir_path(d, t[1])
        outfilename = os.path.join(outdir, fname)
        install_mode = t[2]
        print('Installing %s to %s' % (fname, outdir))
        d.dirmaker.makedirs(outdir, exist_ok=True)
        do_copyfile(fullfilename, outfilename)
        set_mode(outfilename, install_mode, d.install_umask)

def run_install_script(d):
    env = {'MESON_SOURCE_ROOT': d.source_dir,
           'MESON_BUILD_ROOT': d.build_dir,
           'MESON_INSTALL_PREFIX': d.prefix,
           'MESON_INSTALL_DESTDIR_PREFIX': d.fullprefix,
           'MESONINTROSPECT': ' '.join([shlex.quote(x) for x in d.mesonintrospect]),
           }

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
        except OSError:
            print('Failed to run install script {!r}'.format(name))
            sys.exit(1)

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
        outname = os.path.join(outdir, os.path.basename(fname))
        final_path = os.path.join(d.prefix, outname)
        aliases = t[2]
        should_strip = t[3]
        install_rpath = t[4]
        install_mode = t[5]
        print('Installing %s to %s' % (fname, outname))
        d.dirmaker.makedirs(outdir, exist_ok=True)
        if not os.path.exists(fname):
            raise RuntimeError('File {!r} could not be found'.format(fname))
        elif os.path.isfile(fname):
            do_copyfile(fname, outname)
            set_mode(outname, install_mode, d.install_umask)
            if should_strip and d.strip_bin is not None:
                if fname.endswith('.jar'):
                    print('Not stripping jar target:', os.path.basename(fname))
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
                set_mode(pdb_outname, install_mode, d.install_umask)
        elif os.path.isdir(fname):
            fname = os.path.join(d.build_dir, fname.rstrip('/'))
            outname = os.path.join(outdir, os.path.basename(fname))
            do_copydir(d, fname, outname, None, install_mode)
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
        if os.path.isfile(outname):
            try:
                depfixer.fix_rpath(outname, install_rpath, final_path,
                                   verbose=False)
            except SystemExit as e:
                if isinstance(e.code, int) and e.code == 0:
                    pass
                else:
                    raise

def run(args):
    if len(args) != 1 and len(args) != 2:
        print('Installer script for Meson. Do not run on your own, mmm\'kay?')
        print('meson_install.py [install info file]')
    datafilename = args[0]
    private_dir = os.path.dirname(datafilename)
    log_dir = os.path.join(private_dir, '../meson-logs')
    if len(args) == 2:
        os.chdir(args[1])
    do_install(log_dir, datafilename)
    install_log_file = None
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
