# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .. import mlog
import contextlib
import urllib.request, os, hashlib, shutil, tempfile, stat
import subprocess
import sys
from pathlib import Path
from . import WrapMode
from ..mesonlib import Popen_safe

try:
    import ssl
    has_ssl = True
    API_ROOT = 'https://wrapdb.mesonbuild.com/v1/'
except ImportError:
    has_ssl = False
    API_ROOT = 'http://wrapdb.mesonbuild.com/v1/'

req_timeout = 600.0
ssl_warning_printed = False

def build_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    ctx.options |= ssl.OP_NO_SSLv2
    ctx.options |= ssl.OP_NO_SSLv3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_default_certs()
    return ctx

def quiet_git(cmd, workingdir):
    pc = subprocess.Popen(['git', '-C', workingdir] + cmd, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pc.communicate()
    if pc.returncode != 0:
        return False, err
    return True, out

def open_wrapdburl(urlstring):
    global ssl_warning_printed
    if has_ssl:
        try:
            return urllib.request.urlopen(urlstring, timeout=req_timeout)# , context=build_ssl_context())
        except urllib.error.URLError:
            if not ssl_warning_printed:
                print('SSL connection failed. Falling back to unencrypted connections.')
                ssl_warning_printed = True
    if not ssl_warning_printed:
        print('Warning: SSL not available, traffic not authenticated.',
              file=sys.stderr)
        ssl_warning_printed = True
    # Trying to open SSL connection to wrapdb fails because the
    # certificate is not known.
    if urlstring.startswith('https'):
        urlstring = 'http' + urlstring[5:]
    return urllib.request.urlopen(urlstring, timeout=req_timeout)


class PackageDefinition:
    def __init__(self, fname):
        self.values = {}
        with open(fname) as ifile:
            first = ifile.readline().strip()

            if first == '[wrap-file]':
                self.type = 'file'
            elif first == '[wrap-git]':
                self.type = 'git'
            elif first == '[wrap-hg]':
                self.type = 'hg'
            elif first == '[wrap-svn]':
                self.type = 'svn'
            else:
                raise RuntimeError('Invalid format of package file')
            for line in ifile:
                line = line.strip()
                if line == '':
                    continue
                (k, v) = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                self.values[k] = v

    def get(self, key):
        return self.values[key]

    def has_patch(self):
        return 'patch_url' in self.values

class Resolver:
    def __init__(self, subdir_root, wrap_mode=WrapMode(1)):
        self.wrap_mode = wrap_mode
        self.subdir_root = subdir_root
        self.cachedir = os.path.join(self.subdir_root, 'packagecache')

    def resolve(self, packagename):
        # Check if the directory is already resolved
        dirname = Path(os.path.join(self.subdir_root, packagename))
        subprojdir = os.path.join(*dirname.parts[-2:])
        if dirname.is_dir():
            if (dirname / 'meson.build').is_file():
                # The directory is there and has meson.build? Great, use it.
                return packagename
            # Is the dir not empty and also not a git submodule dir that is
            # not checkout properly? Can't do anything, exception!
            elif next(dirname.iterdir(), None) and not (dirname / '.git').is_file():
                m = '{!r} is not empty and has no meson.build files'
                raise RuntimeError(m.format(subprojdir))
        elif dirname.exists():
            m = '{!r} already exists and is not a dir; cannot use as subproject'
            raise RuntimeError(m.format(subprojdir))

        dirname = str(dirname)
        # Check if the subproject is a git submodule
        if self.resolve_git_submodule(dirname):
            return packagename

        # Don't download subproject data based on wrap file if requested.
        # Git submodules are ok (see above)!
        if self.wrap_mode is WrapMode.nodownload:
            m = 'Automatic wrap-based subproject downloading is disabled'
            raise RuntimeError(m)

        # Check if there's a .wrap file for this subproject
        fname = os.path.join(self.subdir_root, packagename + '.wrap')
        if not os.path.isfile(fname):
            # No wrap file with this name? Give up.
            m = 'No {}.wrap found for {!r}'
            raise RuntimeError(m.format(packagename, subprojdir))
        p = PackageDefinition(fname)
        if p.type == 'file':
            if not os.path.isdir(self.cachedir):
                os.mkdir(self.cachedir)
            self.download(p, packagename)
            self.extract_package(p)
        elif p.type == 'git':
            self.get_git(p)
        elif p.type == "hg":
            self.get_hg(p)
        elif p.type == "svn":
            self.get_svn(p)
        else:
            raise AssertionError('Unreachable code.')
        return p.get('directory')

    def resolve_git_submodule(self, dirname):
        # Are we in a git repository?
        ret, out = quiet_git(['rev-parse'], self.subdir_root)
        if not ret:
            return False
        # Is `dirname` a submodule?
        ret, out = quiet_git(['submodule', 'status', dirname], self.subdir_root)
        if not ret:
            return False
        # Submodule has not been added, add it
        if out.startswith(b'+'):
            mlog.warning('git submodule {} might be out of date'.format(dirname))
            return True
        elif out.startswith(b'U'):
            raise RuntimeError('submodule {} has merge conflicts'.format(dirname))
        # Submodule exists, but is deinitialized or wasn't initialized
        elif out.startswith(b'-'):
            if subprocess.call(['git', '-C', self.subdir_root, 'submodule', 'update', '--init', dirname]) == 0:
                return True
            raise RuntimeError('Failed to git submodule init {!r}'.format(dirname))
        # Submodule looks fine, but maybe it wasn't populated properly. Do a checkout.
        elif out.startswith(b' '):
            subprocess.call(['git', 'checkout', '.'], cwd=dirname)
            # Even if checkout failed, try building it anyway and let the user
            # handle any problems manually.
            return True
        m = 'Unknown git submodule output: {!r}'
        raise RuntimeError(m.format(out))

    def get_git(self, p):
        checkoutdir = os.path.join(self.subdir_root, p.get('directory'))
        revno = p.get('revision')
        is_there = os.path.isdir(checkoutdir)
        if is_there:
            try:
                subprocess.check_call(['git', 'rev-parse'], cwd=checkoutdir)
            except subprocess.CalledProcessError:
                raise RuntimeError('%s is not empty but is not a valid '
                                   'git repository, we can not work with it'
                                   ' as a subproject directory.' % (
                                       checkoutdir))

            if revno.lower() == 'head':
                # Failure to do pull is not a fatal error,
                # because otherwise you can't develop without
                # a working net connection.
                subprocess.call(['git', 'pull'], cwd=checkoutdir)
            else:
                if subprocess.call(['git', 'checkout', revno], cwd=checkoutdir) != 0:
                    subprocess.check_call(['git', 'fetch', p.get('url'), revno], cwd=checkoutdir)
                    subprocess.check_call(['git', 'checkout', revno],
                                          cwd=checkoutdir)
        else:
            if p.values.get('clone-recursive', '').lower() == 'true':
                subprocess.check_call(['git', 'clone', '--recursive', p.get('url'),
                                       p.get('directory')], cwd=self.subdir_root)
            else:
                subprocess.check_call(['git', 'clone', p.get('url'),
                                       p.get('directory')], cwd=self.subdir_root)
            if revno.lower() != 'head':
                if subprocess.call(['git', 'checkout', revno], cwd=checkoutdir) != 0:
                    subprocess.check_call(['git', 'fetch', p.get('url'), revno], cwd=checkoutdir)
                    subprocess.check_call(['git', 'checkout', revno],
                                          cwd=checkoutdir)
            push_url = p.values.get('push-url')
            if push_url:
                subprocess.check_call(['git', 'remote', 'set-url',
                                       '--push', 'origin', push_url],
                                      cwd=checkoutdir)

    def get_hg(self, p):
        checkoutdir = os.path.join(self.subdir_root, p.get('directory'))
        revno = p.get('revision')
        is_there = os.path.isdir(checkoutdir)
        if is_there:
            if revno.lower() == 'tip':
                # Failure to do pull is not a fatal error,
                # because otherwise you can't develop without
                # a working net connection.
                subprocess.call(['hg', 'pull'], cwd=checkoutdir)
            else:
                if subprocess.call(['hg', 'checkout', revno], cwd=checkoutdir) != 0:
                    subprocess.check_call(['hg', 'pull'], cwd=checkoutdir)
                    subprocess.check_call(['hg', 'checkout', revno],
                                          cwd=checkoutdir)
        else:
            subprocess.check_call(['hg', 'clone', p.get('url'),
                                   p.get('directory')], cwd=self.subdir_root)
            if revno.lower() != 'tip':
                subprocess.check_call(['hg', 'checkout', revno],
                                      cwd=checkoutdir)

    def get_svn(self, p):
        checkoutdir = os.path.join(self.subdir_root, p.get('directory'))
        revno = p.get('revision')
        is_there = os.path.isdir(checkoutdir)
        if is_there:
            p, out = Popen_safe(['svn', 'info', '--show-item', 'revision', checkoutdir])
            current_revno = out
            if current_revno == revno:
                return

            if revno.lower() == 'head':
                # Failure to do pull is not a fatal error,
                # because otherwise you can't develop without
                # a working net connection.
                subprocess.call(['svn', 'update'], cwd=checkoutdir)
            else:
                subprocess.check_call(['svn', 'update', '-r', revno], cwd=checkoutdir)
        else:
            subprocess.check_call(['svn', 'checkout', '-r', revno, p.get('url'),
                                   p.get('directory')], cwd=self.subdir_root)

    def get_data(self, url):
        blocksize = 10 * 1024
        h = hashlib.sha256()
        tmpfile = tempfile.NamedTemporaryFile(mode='wb', dir=self.cachedir, delete=False)
        if url.startswith('https://wrapdb.mesonbuild.com'):
            resp = open_wrapdburl(url)
        else:
            resp = urllib.request.urlopen(url, timeout=req_timeout)
        with contextlib.closing(resp) as resp:
            try:
                dlsize = int(resp.info()['Content-Length'])
            except TypeError:
                dlsize = None
            if dlsize is None:
                print('Downloading file of unknown size.')
                while True:
                    block = resp.read(blocksize)
                    if block == b'':
                        break
                    h.update(block)
                    tmpfile.write(block)
                hashvalue = h.hexdigest()
                return hashvalue, tmpfile.name
            print('Download size:', dlsize)
            print('Downloading: ', end='')
            sys.stdout.flush()
            printed_dots = 0
            downloaded = 0
            while True:
                block = resp.read(blocksize)
                if block == b'':
                    break
                downloaded += len(block)
                h.update(block)
                tmpfile.write(block)
                ratio = int(downloaded / dlsize * 10)
                while printed_dots < ratio:
                    print('.', end='')
                    sys.stdout.flush()
                    printed_dots += 1
            print('')
            hashvalue = h.hexdigest()
        return hashvalue, tmpfile.name

    def get_hash(self, data):
        h = hashlib.sha256()
        h.update(data)
        hashvalue = h.hexdigest()
        return hashvalue

    def download(self, p, packagename):
        ofname = os.path.join(self.cachedir, p.get('source_filename'))
        if os.path.exists(ofname):
            mlog.log('Using', mlog.bold(packagename), 'from cache.')
        else:
            srcurl = p.get('source_url')
            mlog.log('Downloading', mlog.bold(packagename), 'from', mlog.bold(srcurl))
            dhash, tmpfile = self.get_data(srcurl)
            expected = p.get('source_hash')
            if dhash != expected:
                os.remove(tmpfile)
                raise RuntimeError('Incorrect hash for source %s:\n %s expected\n %s actual.' % (packagename, expected, dhash))
            os.rename(tmpfile, ofname)
        if p.has_patch():
            patch_filename = p.get('patch_filename')
            filename = os.path.join(self.cachedir, patch_filename)
            if os.path.exists(filename):
                mlog.log('Using', mlog.bold(patch_filename), 'from cache.')
            else:
                purl = p.get('patch_url')
                mlog.log('Downloading patch from', mlog.bold(purl))
                phash, tmpfile = self.get_data(purl)
                expected = p.get('patch_hash')
                if phash != expected:
                    os.remove(tmpfile)
                    raise RuntimeError('Incorrect hash for patch %s:\n %s expected\n %s actual' % (packagename, expected, phash))
                os.rename(tmpfile, filename)
        else:
            mlog.log('Package does not require patch.')

    def copy_tree(self, root_src_dir, root_dst_dir):
        """
        Copy directory tree. Overwrites also read only files.
        """
        for src_dir, dirs, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    try:
                        os.remove(dst_file)
                    except PermissionError as exc:
                        os.chmod(dst_file, stat.S_IWUSR)
                        os.remove(dst_file)
                shutil.copy2(src_file, dst_dir)

    def extract_package(self, package):
        if sys.version_info < (3, 5):
            try:
                import lzma # noqa: F401
                del lzma
            except ImportError:
                pass
            else:
                try:
                    shutil.register_unpack_format('xztar', ['.tar.xz', '.txz'], shutil._unpack_tarfile, [], "xz'ed tar-file")
                except shutil.RegistryError:
                    pass
        target_dir = os.path.join(self.subdir_root, package.get('directory'))
        if os.path.isdir(target_dir):
            return
        extract_dir = self.subdir_root
        # Some upstreams ship packages that do not have a leading directory.
        # Create one for them.
        try:
            package.get('lead_directory_missing')
            os.mkdir(target_dir)
            extract_dir = target_dir
        except KeyError:
            pass
        shutil.unpack_archive(os.path.join(self.cachedir, package.get('source_filename')), extract_dir)
        if package.has_patch():
            try:
                shutil.unpack_archive(os.path.join(self.cachedir, package.get('patch_filename')), self.subdir_root)
            except Exception:
                with tempfile.TemporaryDirectory() as workdir:
                    shutil.unpack_archive(os.path.join(self.cachedir, package.get('patch_filename')), workdir)
                    self.copy_tree(workdir, self.subdir_root)
