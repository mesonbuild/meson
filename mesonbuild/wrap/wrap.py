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
import configparser
from . import WrapMode
from ..mesonlib import MesonException

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
    try:
        pc = subprocess.Popen(['git', '-C', workingdir] + cmd, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        return False, str(e)
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

class WrapException(MesonException):
    pass

class WrapNotFoundException(WrapException):
    pass

class PackageDefinition:
    def __init__(self, fname):
        self.filename = fname
        self.basename = os.path.basename(fname)
        self.name = self.basename[:-5]
        try:
            self.config = configparser.ConfigParser(interpolation=None)
            self.config.read(fname)
        except configparser.Error:
            raise WrapException('Failed to parse {}'.format(self.basename))
        if len(self.config.sections()) < 1:
            raise WrapException('Missing sections in {}'.format(self.basename))
        self.wrap_section = self.config.sections()[0]
        if not self.wrap_section.startswith('wrap-'):
            m = '{!r} is not a valid first section in {}'
            raise WrapException(m.format(self.wrap_section, self.basename))
        self.type = self.wrap_section[5:]
        self.values = dict(self.config[self.wrap_section])

    def get(self, key):
        try:
            return self.values[key]
        except KeyError:
            m = 'Missing key {!r} in {}'
            raise WrapException(m.format(key, self.basename))

    def has_patch(self):
        return 'patch_url' in self.values

class Resolver:
    def __init__(self, subdir_root, wrap_mode=WrapMode.default):
        self.wrap_mode = wrap_mode
        self.subdir_root = subdir_root
        self.cachedir = os.path.join(self.subdir_root, 'packagecache')

    def resolve(self, packagename: str, method: str):
        self.packagename = packagename
        self.directory = packagename
        # We always have to load the wrap file, if it exists, because it could
        # override the default directory name.
        self.wrap = self.load_wrap()
        if self.wrap and 'directory' in self.wrap.values:
            self.directory = self.wrap.get('directory')
            if os.path.dirname(self.directory):
                raise WrapException('Directory key must be a name and not a path')
        self.dirname = os.path.join(self.subdir_root, self.directory)
        meson_file = os.path.join(self.dirname, 'meson.build')
        cmake_file = os.path.join(self.dirname, 'CMakeLists.txt')

        if method not in ['meson', 'cmake']:
            raise WrapException('Only the methods "meson" and "cmake" are supported')

        # The directory is there and has meson.build? Great, use it.
        if method == 'meson' and os.path.exists(meson_file):
            return self.directory
        if method == 'cmake' and os.path.exists(cmake_file):
            return self.directory

        # Check if the subproject is a git submodule
        self.resolve_git_submodule()

        if os.path.exists(self.dirname):
            if not os.path.isdir(self.dirname):
                raise WrapException('Path already exists but is not a directory')
        else:
            # A wrap file is required to download
            if not self.wrap:
                m = 'Subproject directory not found and {}.wrap file not found'
                raise WrapNotFoundException(m.format(self.packagename))

            if self.wrap.type == 'file':
                self.get_file()
            else:
                self.check_can_download()
                if self.wrap.type == 'git':
                    self.get_git()
                elif self.wrap.type == "hg":
                    self.get_hg()
                elif self.wrap.type == "svn":
                    self.get_svn()
                else:
                    raise WrapException('Unknown wrap type {!r}'.format(self.wrap.type))

        # A meson.build or CMakeLists.txt file is required in the directory
        if method == 'meson' and not os.path.exists(meson_file):
            raise WrapException('Subproject exists but has no meson.build file')
        if method == 'cmake' and not os.path.exists(cmake_file):
            raise WrapException('Subproject exists but has no CMakeLists.txt file')

        return self.directory

    def load_wrap(self):
        fname = os.path.join(self.subdir_root, self.packagename + '.wrap')
        if os.path.isfile(fname):
            return PackageDefinition(fname)
        return None

    def check_can_download(self):
        # Don't download subproject data based on wrap file if requested.
        # Git submodules are ok (see above)!
        if self.wrap_mode is WrapMode.nodownload:
            m = 'Automatic wrap-based subproject downloading is disabled'
            raise WrapException(m)

    def resolve_git_submodule(self):
        # Are we in a git repository?
        ret, out = quiet_git(['rev-parse'], self.subdir_root)
        if not ret:
            return False
        # Is `dirname` a submodule?
        ret, out = quiet_git(['submodule', 'status', self.dirname], self.subdir_root)
        if not ret:
            return False
        # Submodule has not been added, add it
        if out.startswith(b'+'):
            mlog.warning('git submodule might be out of date')
            return True
        elif out.startswith(b'U'):
            raise WrapException('git submodule has merge conflicts')
        # Submodule exists, but is deinitialized or wasn't initialized
        elif out.startswith(b'-'):
            if subprocess.call(['git', '-C', self.subdir_root, 'submodule', 'update', '--init', self.dirname]) == 0:
                return True
            raise WrapException('git submodule failed to init')
        # Submodule looks fine, but maybe it wasn't populated properly. Do a checkout.
        elif out.startswith(b' '):
            subprocess.call(['git', 'checkout', '.'], cwd=self.dirname)
            # Even if checkout failed, try building it anyway and let the user
            # handle any problems manually.
            return True
        elif out == b'':
            # It is not a submodule, just a folder that exists in the main repository.
            return False
        m = 'Unknown git submodule output: {!r}'
        raise WrapException(m.format(out))

    def get_file(self):
        path = self.get_file_internal('source')
        extract_dir = self.subdir_root
        # Some upstreams ship packages that do not have a leading directory.
        # Create one for them.
        if 'lead_directory_missing' in self.wrap.values:
            os.mkdir(self.dirname)
            extract_dir = self.dirname
        shutil.unpack_archive(path, extract_dir)
        if self.wrap.has_patch():
            self.apply_patch()

    def get_git(self):
        revno = self.wrap.get('revision')
        subprocess.check_call(['git', 'clone', self.wrap.get('url'),
                               self.directory], cwd=self.subdir_root)
        if revno.lower() != 'head':
            if subprocess.call(['git', 'checkout', revno], cwd=self.dirname) != 0:
                subprocess.check_call(['git', 'fetch', self.wrap.get('url'), revno], cwd=self.dirname)
                subprocess.check_call(['git', 'checkout', revno], cwd=self.dirname)
        if self.wrap.values.get('clone-recursive', '').lower() == 'true':
            subprocess.check_call(['git', 'submodule', 'update',
                                   '--init', '--checkout', '--recursive'],
                                  cwd=self.dirname)
        push_url = self.wrap.values.get('push-url')
        if push_url:
            subprocess.check_call(['git', 'remote', 'set-url',
                                   '--push', 'origin', push_url],
                                  cwd=self.dirname)

    def get_hg(self):
        revno = self.wrap.get('revision')
        subprocess.check_call(['hg', 'clone', self.wrap.get('url'),
                               self.directory], cwd=self.subdir_root)
        if revno.lower() != 'tip':
            subprocess.check_call(['hg', 'checkout', revno],
                                  cwd=self.dirname)

    def get_svn(self):
        revno = self.wrap.get('revision')
        subprocess.check_call(['svn', 'checkout', '-r', revno, self.wrap.get('url'),
                               self.directory], cwd=self.subdir_root)

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

    def check_hash(self, what, path):
        expected = self.wrap.get(what + '_hash')
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            h.update(f.read())
        dhash = h.hexdigest()
        if dhash != expected:
            raise WrapException('Incorrect hash for %s:\n %s expected\n %s actual.' % (what, expected, dhash))

    def download(self, what, ofname):
        self.check_can_download()
        srcurl = self.wrap.get(what + '_url')
        mlog.log('Downloading', mlog.bold(self.packagename), what, 'from', mlog.bold(srcurl))
        dhash, tmpfile = self.get_data(srcurl)
        expected = self.wrap.get(what + '_hash')
        if dhash != expected:
            os.remove(tmpfile)
            raise WrapException('Incorrect hash for %s:\n %s expected\n %s actual.' % (what, expected, dhash))
        os.rename(tmpfile, ofname)

    def get_file_internal(self, what):
        filename = self.wrap.get(what + '_filename')
        cache_path = os.path.join(self.cachedir, filename)

        if os.path.exists(cache_path):
            self.check_hash(what, cache_path)
            mlog.log('Using', mlog.bold(self.packagename), what, 'from cache.')
            return cache_path

        if not os.path.isdir(self.cachedir):
            os.mkdir(self.cachedir)
        self.download(what, cache_path)
        return cache_path

    def apply_patch(self):
        path = self.get_file_internal('patch')
        try:
            shutil.unpack_archive(path, self.subdir_root)
        except Exception:
            with tempfile.TemporaryDirectory() as workdir:
                shutil.unpack_archive(path, workdir)
                self.copy_tree(workdir, self.subdir_root)

    def copy_tree(self, root_src_dir, root_dst_dir):
        """
        Copy directory tree. Overwrites also read only files.
        """
        for src_dir, _, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    try:
                        os.remove(dst_file)
                    except PermissionError:
                        os.chmod(dst_file, stat.S_IWUSR)
                        os.remove(dst_file)
                shutil.copy2(src_file, dst_dir)
