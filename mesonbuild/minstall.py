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
import argparse
from glob import glob
from .scripts import depfixer
from .scripts import destdir_join
from .mesonlib import is_windows, Popen_safe
from .mtest import rebuild_all
try:
    from __main__ import __file__ as main_file
except ImportError:
    # Happens when running as meson.exe which is native Windows.
    # This is only used for pkexec which is not, so this is fine.
    main_file = None

symlink_warning = '''Warning: trying to copy a symlink that points to a file. This will copy the file,
but this will be changed in a future version of Meson to copy the symlink as is. Please update your
build definitions so that it will not break when the change happens.'''

selinux_updates = []

def buildparser():
    parser = argparse.ArgumentParser(prog='meson install')
    parser.add_argument('-C', default='.', dest='wd',
                        help='directory to cd into before running')
    parser.add_argument('--no-rebuild', default=False, action='store_true',
                        help='Do not rebuild before installing.')
    parser.add_argument('--only-changed', default=False, action='store_true',
                        help='Only overwrite files that are older than the copied file.')
    return parser

class DirMaker:
    def __init__(self, lf):
        self.lf = lf
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
            append_to_log(self.lf, d)

def is_executable(path, follow_symlinks=False):
    '''Checks whether any of the "x" bits are set in the source file mode.'''
    return bool(os.stat(path, follow_symlinks=follow_symlinks).st_mode & 0o111)

def append_to_log(lf, line):
    lf.write(line)
    if not line.endswith('\n'):
        lf.write('\n')
    lf.flush()

def set_chown(path, user=None, group=None, dir_fd=None, follow_symlinks=True):
    # shutil.chown will call os.chown without passing all the parameters
    # and particularly follow_symlinks, thus we replace it temporary
    # with a lambda with all the parameters so that follow_symlinks will
    # be actually passed properly.
    # Not nice, but better than actually rewriting shutil.chown until
    # this python bug is fixed: https://bugs.python.org/issue18108
    real_os_chown = os.chown
    try:
        os.chown = lambda p, u, g: real_os_chown(p, u, g,
                                                 dir_fd=dir_fd,
                                                 follow_symlinks=follow_symlinks)
        shutil.chown(path, user, group)
    except:
        raise
    finally:
        os.chown = real_os_chown

def set_chmod(path, mode, dir_fd=None, follow_symlinks=True):
    try:
        os.chmod(path, mode, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
    except (NotImplementedError, OSError, SystemError) as e:
        if not os.path.islink(path):
            os.chmod(path, mode, dir_fd=dir_fd)

def sanitize_permissions(path, umask):
    if umask is None:
        return
    new_perms = 0o777 if is_executable(path, follow_symlinks=False) else 0o666
    new_perms &= ~umask
    try:
        set_chmod(path, new_perms, follow_symlinks=False)
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
            set_chown(path, mode.owner, mode.group, follow_symlinks=False)
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
            set_chmod(path, mode.perms, follow_symlinks=False)
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


def get_destdir_path(d, path):
    if os.path.isabs(path):
        output = destdir_join(d.destdir, path)
    else:
        output = os.path.join(d.fullprefix, path)
    return output


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

class Installer:

    def __init__(self, options, lf):
        self.options = options
        self.lf = lf

    def should_preserve_existing_file(self, from_file, to_file):
        if not self.options.only_changed:
            return False
        # Always replace danging symlinks
        if os.path.islink(from_file) and not os.path.isfile(from_file):
            return False
        from_time = os.stat(from_file).st_mtime
        to_time = os.stat(to_file).st_mtime
        return from_time <= to_time

    def do_copyfile(self, from_file, to_file):
        outdir = os.path.split(to_file)[0]
        if not os.path.isfile(from_file) and not os.path.islink(from_file):
            raise RuntimeError('Tried to install something that isn\'t a file:'
                               '{!r}'.format(from_file))
        # copyfile fails if the target file already exists, so remove it to
        # allow overwriting a previous install. If the target is not a file, we
        # want to give a readable error.
        if os.path.exists(to_file):
            if not os.path.isfile(to_file):
                raise RuntimeError('Destination {!r} already exists and is not '
                                   'a file'.format(to_file))
            if self.should_preserve_existing_file(from_file, to_file):
                append_to_log(self.lf, '# Preserving old file %s\n' % to_file)
                print('Preserving existing file %s.' % to_file)
                return False
            os.remove(to_file)
        print('Installing %s to %s' % (from_file, outdir))
        if os.path.islink(from_file):
            if not os.path.exists(from_file):
                # Dangling symlink. Replicate as is.
                shutil.copy(from_file, outdir, follow_symlinks=False)
            else:
                # Remove this entire branch when changing the behaviour to duplicate
                # symlinks rather than copying what they point to.
                print(symlink_warning)
                shutil.copyfile(from_file, to_file)
                shutil.copystat(from_file, to_file)
        else:
            shutil.copyfile(from_file, to_file)
            shutil.copystat(from_file, to_file)
        selinux_updates.append(to_file)
        append_to_log(self.lf, to_file)
        return True

    def do_copydir(self, data, src_dir, dst_dir, exclude, install_mode):
        '''
        Copies the contents of directory @src_dir into @dst_dir.

        For directory
            /foo/
              bar/
                excluded
                foobar
              file
        do_copydir(..., '/foo', '/dst/dir', {'bar/excluded'}) creates
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
                    os.remove(abs_dst)
                parent_dir = os.path.dirname(abs_dst)
                if not os.path.isdir(parent_dir):
                    os.mkdir(parent_dir)
                    shutil.copystat(os.path.dirname(abs_src), parent_dir)
                # FIXME: what about symlinks?
                self.do_copyfile(abs_src, abs_dst)
                set_mode(abs_dst, install_mode, data.install_umask)
                append_to_log(self.lf, abs_dst)

    def do_install(self, datafilename):
        with open(datafilename, 'rb') as ifile:
            d = pickle.load(ifile)
        d.destdir = os.environ.get('DESTDIR', '')
        d.fullprefix = destdir_join(d.destdir, d.prefix)

        if d.install_umask is not None:
            os.umask(d.install_umask)

        try:
            d.dirmaker = DirMaker(self.lf)
            with d.dirmaker:
                self.install_subdirs(d) # Must be first, because it needs to delete the old subtree.
                self.install_targets(d)
                self.install_headers(d)
                self.install_man(d)
                self.install_data(d)
                restore_selinux_contexts()
                self.run_install_script(d)
        except PermissionError:
            if shutil.which('pkexec') is not None and 'PKEXEC_UID' not in os.environ:
                print('Installation failed due to insufficient permissions.')
                print('Attempting to use polkit to gain elevated privileges...')
                os.execlp('pkexec', 'pkexec', sys.executable, main_file, *sys.argv[1:],
                          '-C', os.getcwd())
            else:
                raise

    def install_subdirs(self, d):
        for (src_dir, dst_dir, mode, exclude) in d.install_subdirs:
            full_dst_dir = get_destdir_path(d, dst_dir)
            print('Installing subdir %s to %s' % (src_dir, full_dst_dir))
            d.dirmaker.makedirs(full_dst_dir, exist_ok=True)
            self.do_copydir(d, src_dir, full_dst_dir, exclude, mode)

    def install_data(self, d):
        for i in d.data:
            fullfilename = i[0]
            outfilename = get_destdir_path(d, i[1])
            mode = i[2]
            outdir = os.path.dirname(outfilename)
            d.dirmaker.makedirs(outdir, exist_ok=True)
            self.do_copyfile(fullfilename, outfilename)
            set_mode(outfilename, mode, d.install_umask)

    def install_man(self, d):
        for m in d.man:
            full_source_filename = m[0]
            outfilename = get_destdir_path(d, m[1])
            outdir = os.path.dirname(outfilename)
            d.dirmaker.makedirs(outdir, exist_ok=True)
            install_mode = m[2]
            if outfilename.endswith('.gz') and not full_source_filename.endswith('.gz'):
                with open(outfilename, 'wb') as of:
                    with open(full_source_filename, 'rb') as sf:
                        # Set mtime and filename for reproducibility.
                        with gzip.GzipFile(fileobj=of, mode='wb', filename='', mtime=0) as gz:
                            gz.write(sf.read())
                shutil.copystat(full_source_filename, outfilename)
                print('Installing %s to %s' % (full_source_filename, outdir))
                append_to_log(self.lf, outfilename)
            else:
                self.do_copyfile(full_source_filename, outfilename)
            set_mode(outfilename, install_mode, d.install_umask)

    def install_headers(self, d):
        for t in d.headers:
            fullfilename = t[0]
            fname = os.path.basename(fullfilename)
            outdir = get_destdir_path(d, t[1])
            outfilename = os.path.join(outdir, fname)
            install_mode = t[2]
            d.dirmaker.makedirs(outdir, exist_ok=True)
            self.do_copyfile(fullfilename, outfilename)
            set_mode(outfilename, install_mode, d.install_umask)

    def run_install_script(self, d):
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

    def install_targets(self, d):
        for t in d.targets:
            if not os.path.exists(t.fname):
                # For example, import libraries of shared modules are optional
                if t.optional:
                    print('File {!r} not found, skipping'.format(t.fname))
                    continue
                else:
                    raise RuntimeError('File {!r} could not be found'.format(t.fname))
            fname = check_for_stampfile(t.fname)
            outdir = get_destdir_path(d, t.outdir)
            outname = os.path.join(outdir, os.path.basename(fname))
            final_path = os.path.join(d.prefix, t.outdir, os.path.basename(fname))
            aliases = t.aliases
            should_strip = t.strip
            install_rpath = t.install_rpath
            install_name_mappings = t.install_name_mappings
            install_mode = t.install_mode
            d.dirmaker.makedirs(outdir, exist_ok=True)
            if not os.path.exists(fname):
                raise RuntimeError('File {!r} could not be found'.format(fname))
            elif os.path.isfile(fname):
                self.do_copyfile(fname, outname)
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
                    self.do_copyfile(pdb_filename, pdb_outname)
                    set_mode(pdb_outname, install_mode, d.install_umask)
            elif os.path.isdir(fname):
                fname = os.path.join(d.build_dir, fname.rstrip('/'))
                outname = os.path.join(outdir, os.path.basename(fname))
                self.do_copydir(d, fname, outname, None, install_mode)
            else:
                raise RuntimeError('Unknown file type for {!r}'.format(fname))
            printed_symlink_error = False
            for alias, to in aliases.items():
                try:
                    symlinkfilename = os.path.join(outdir, alias)
                    try:
                        os.remove(symlinkfilename)
                    except FileNotFoundError:
                        pass
                    os.symlink(to, symlinkfilename)
                    append_to_log(self.lf, symlinkfilename)
                except (NotImplementedError, OSError):
                    if not printed_symlink_error:
                        print("Symlink creation does not work on this platform. "
                              "Skipping all symlinking.")
                        printed_symlink_error = True
            if os.path.isfile(outname):
                try:
                    depfixer.fix_rpath(outname, install_rpath, final_path,
                                       install_name_mappings, verbose=False)
                except SystemExit as e:
                    if isinstance(e.code, int) and e.code == 0:
                        pass
                    else:
                        raise

def run(args):
    parser = buildparser()
    opts = parser.parse_args(args)
    datafilename = 'meson-private/install.dat'
    private_dir = os.path.dirname(datafilename)
    log_dir = os.path.join(private_dir, '../meson-logs')
    if not os.path.exists(os.path.join(opts.wd, datafilename)):
        sys.exit('Install data not found. Run this command in build directory root.')
    log_dir = os.path.join(private_dir, '../meson-logs')
    if not opts.no_rebuild:
        if not rebuild_all(opts.wd):
            sys.exit(-1)
    os.chdir(opts.wd)
    with open(os.path.join(log_dir, 'install-log.txt'), 'w') as lf:
        installer = Installer(opts, lf)
        append_to_log(lf, '# List of files installed by Meson')
        append_to_log(lf, '# Does not contain files installed by custom scripts.')
        installer.do_install(datafilename)
    return 0

if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
