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
from dataclasses import dataclass
import urllib.request
import urllib.error
import urllib.parse
import os
import hashlib
import shutil
import tempfile
import stat
import subprocess
import sys
import configparser
import time
import typing as T
import textwrap

from pathlib import Path
from . import WrapMode
from .. import coredata
from ..mesonlib import quiet_git, GIT, ProgressBar, MesonException, windows_proof_rmtree
from ..interpreterbase import FeatureNew
from ..interpreterbase import SubProject
from .. import mesonlib

if T.TYPE_CHECKING:
    import http.client

try:
    # Importing is just done to check if SSL exists, so all warnings
    # regarding 'imported but unused' can be safely ignored
    import ssl  # noqa
    has_ssl = True
except ImportError:
    has_ssl = False

REQ_TIMEOUT = 600.0
SSL_WARNING_PRINTED = False
WHITELIST_SUBDOMAIN = 'wrapdb.mesonbuild.com'

ALL_TYPES = ['file', 'git', 'hg', 'svn']

def whitelist_wrapdb(urlstr: str) -> urllib.parse.ParseResult:
    """ raises WrapException if not whitelisted subdomain """
    url = urllib.parse.urlparse(urlstr)
    if not url.hostname:
        raise WrapException(f'{urlstr} is not a valid URL')
    if not url.hostname.endswith(WHITELIST_SUBDOMAIN):
        raise WrapException(f'{urlstr} is not a whitelisted WrapDB URL')
    if has_ssl and not url.scheme == 'https':
        raise WrapException(f'WrapDB did not have expected SSL https url, instead got {urlstr}')
    return url

def open_wrapdburl(urlstring: str) -> 'http.client.HTTPResponse':
    global SSL_WARNING_PRINTED

    url = whitelist_wrapdb(urlstring)
    if has_ssl:
        try:
            return T.cast('http.client.HTTPResponse', urllib.request.urlopen(urllib.parse.urlunparse(url), timeout=REQ_TIMEOUT))
        except urllib.error.URLError as excp:
            raise WrapException(f'WrapDB connection failed to {urlstring} with error {excp}')

    # following code is only for those without Python SSL
    nossl_url = url._replace(scheme='http')
    if not SSL_WARNING_PRINTED:
        mlog.warning(f'SSL module not available in {sys.executable}: WrapDB traffic not authenticated.')
        SSL_WARNING_PRINTED = True
    try:
        return T.cast('http.client.HTTPResponse', urllib.request.urlopen(urllib.parse.urlunparse(nossl_url), timeout=REQ_TIMEOUT))
    except urllib.error.URLError as excp:
        raise WrapException(f'WrapDB connection failed to {urlstring} with error {excp}')


class WrapException(MesonException):
    pass

class WrapNotFoundException(WrapException):
    pass

class PackageDefinition:
    def __init__(self, fname: str, subproject: str = ''):
        self.filename = fname
        self.subproject = SubProject(subproject)
        self.type = None  # type: T.Optional[str]
        self.values = {} # type: T.Dict[str, str]
        self.provided_deps = {} # type: T.Dict[str, T.Optional[str]]
        self.provided_programs = [] # type: T.List[str]
        self.basename = os.path.basename(fname)
        self.has_wrap = self.basename.endswith('.wrap')
        self.name = self.basename[:-5] if self.has_wrap else self.basename
        self.directory = self.name
        self.provided_deps[self.name] = None
        self.original_filename = fname
        self.redirected = False
        if self.has_wrap:
            self.parse_wrap()
        self.directory = self.values.get('directory', self.name)
        if os.path.dirname(self.directory):
            raise WrapException('Directory key must be a name and not a path')
        if self.type and self.type not in ALL_TYPES:
            raise WrapException(f'Unknown wrap type {self.type!r}')
        self.filesdir = os.path.join(os.path.dirname(self.filename), 'packagefiles')
        # What the original file name was before redirection

    def parse_wrap(self) -> None:
        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.filename, encoding='utf-8')
        except configparser.Error as e:
            raise WrapException(f'Failed to parse {self.basename}: {e!s}')
        self.parse_wrap_section(config)
        if self.type == 'redirect':
            # [wrap-redirect] have a `filename` value pointing to the real wrap
            # file we should parse instead. It must be relative to the current
            # wrap file location and must be in the form foo/subprojects/bar.wrap.
            dirname = Path(self.filename).parent
            fname = Path(self.values['filename'])
            for i, p in enumerate(fname.parts):
                if i % 2 == 0:
                    if p == '..':
                        raise WrapException('wrap-redirect filename cannot contain ".."')
                else:
                    if p != 'subprojects':
                        raise WrapException('wrap-redirect filename must be in the form foo/subprojects/bar.wrap')
            if fname.suffix != '.wrap':
                raise WrapException('wrap-redirect filename must be a .wrap file')
            fname = dirname / fname
            if not fname.is_file():
                raise WrapException(f'wrap-redirect {fname} filename does not exist')
            self.filename = str(fname)
            self.parse_wrap()
            self.redirected = True
        else:
            self.parse_provide_section(config)
        if 'patch_directory' in self.values:
            FeatureNew('Wrap files with patch_directory', '0.55.0').use(self.subproject)
        for what in ['patch', 'source']:
            if f'{what}_filename' in self.values and f'{what}_url' not in self.values:
                FeatureNew(f'Local wrap patch files without {what}_url', '0.55.0').use(self.subproject)

    def parse_wrap_section(self, config: configparser.ConfigParser) -> None:
        if len(config.sections()) < 1:
            raise WrapException(f'Missing sections in {self.basename}')
        self.wrap_section = config.sections()[0]
        if not self.wrap_section.startswith('wrap-'):
            raise WrapException(f'{self.wrap_section!r} is not a valid first section in {self.basename}')
        self.type = self.wrap_section[5:]
        self.values = dict(config[self.wrap_section])

    def parse_provide_section(self, config: configparser.ConfigParser) -> None:
        if config.has_section('provide'):
            for k, v in config['provide'].items():
                if k == 'dependency_names':
                    # A comma separated list of dependency names that does not
                    # need a variable name
                    names_dict = {n.strip(): None for n in v.split(',')}
                    self.provided_deps.update(names_dict)
                    continue
                if k == 'program_names':
                    # A comma separated list of program names
                    names_list = [n.strip() for n in v.split(',')]
                    self.provided_programs += names_list
                    continue
                if not v:
                    m = (f'Empty dependency variable name for {k!r} in {self.basename}. '
                         'If the subproject uses meson.override_dependency() '
                         'it can be added in the "dependency_names" special key.')
                    raise WrapException(m)
                self.provided_deps[k] = v

    def get(self, key: str) -> str:
        try:
            return self.values[key]
        except KeyError:
            raise WrapException(f'Missing key {key!r} in {self.basename}')

def get_directory(subdir_root: str, packagename: str) -> str:
    fname = os.path.join(subdir_root, packagename + '.wrap')
    if os.path.isfile(fname):
        wrap = PackageDefinition(fname)
        return wrap.directory
    return packagename

def verbose_git(cmd: T.List[str], workingdir: str, check: bool = False) -> bool:
    '''
    Wrapper to convert GitException to WrapException caught in interpreter.
    '''
    try:
        return mesonlib.verbose_git(cmd, workingdir, check=check)
    except mesonlib.GitException as e:
        raise WrapException(str(e))

@dataclass(eq=False)
class Resolver:
    source_dir: str
    subdir: str
    subproject: str = ''
    wrap_mode: WrapMode = WrapMode.default

    def __post_init__(self) -> None:
        self.subdir_root = os.path.join(self.source_dir, self.subdir)
        self.cachedir = os.path.join(self.subdir_root, 'packagecache')
        self.wraps = {} # type: T.Dict[str, PackageDefinition]
        self.provided_deps = {} # type: T.Dict[str, PackageDefinition]
        self.provided_programs = {} # type: T.Dict[str, PackageDefinition]
        self.load_wraps()

    def load_wraps(self) -> None:
        if not os.path.isdir(self.subdir_root):
            return
        root, dirs, files = next(os.walk(self.subdir_root))
        for i in files:
            if not i.endswith('.wrap'):
                continue
            fname = os.path.join(self.subdir_root, i)
            wrap = PackageDefinition(fname, self.subproject)
            self.wraps[wrap.name] = wrap
            if wrap.directory in dirs:
                dirs.remove(wrap.directory)
        # Add dummy package definition for directories not associated with a wrap file.
        for i in dirs:
            if i in ['packagecache', 'packagefiles']:
                continue
            fname = os.path.join(self.subdir_root, i)
            wrap = PackageDefinition(fname, self.subproject)
            self.wraps[wrap.name] = wrap

        for wrap in self.wraps.values():
            for k in wrap.provided_deps.keys():
                if k in self.provided_deps:
                    prev_wrap = self.provided_deps[k]
                    m = f'Multiple wrap files provide {k!r} dependency: {wrap.basename} and {prev_wrap.basename}'
                    raise WrapException(m)
                self.provided_deps[k] = wrap
            for k in wrap.provided_programs:
                if k in self.provided_programs:
                    prev_wrap = self.provided_programs[k]
                    m = f'Multiple wrap files provide {k!r} program: {wrap.basename} and {prev_wrap.basename}'
                    raise WrapException(m)
                self.provided_programs[k] = wrap

    def merge_wraps(self, other_resolver: 'Resolver') -> None:
        for k, v in other_resolver.wraps.items():
            self.wraps.setdefault(k, v)
        for k, v in other_resolver.provided_deps.items():
            self.provided_deps.setdefault(k, v)
        for k, v in other_resolver.provided_programs.items():
            self.provided_programs.setdefault(k, v)

    def find_dep_provider(self, packagename: str) -> T.Tuple[T.Optional[str], T.Optional[str]]:
        # Python's ini parser converts all key values to lowercase.
        # Thus the query name must also be in lower case.
        packagename = packagename.lower()
        wrap = self.provided_deps.get(packagename)
        if wrap:
            dep_var = wrap.provided_deps.get(packagename)
            return wrap.name, dep_var
        return None, None

    def get_varname(self, subp_name: str, depname: str) -> T.Optional[str]:
        wrap = self.wraps.get(subp_name)
        return wrap.provided_deps.get(depname) if wrap else None

    def find_program_provider(self, names: T.List[str]) -> T.Optional[str]:
        for name in names:
            wrap = self.provided_programs.get(name)
            if wrap:
                return wrap.name
        return None

    def resolve(self, packagename: str, method: str) -> str:
        self.packagename = packagename
        self.directory = packagename
        self.wrap = self.wraps.get(packagename)
        if not self.wrap:
            m = f'Neither a subproject directory nor a {self.packagename}.wrap file was found.'
            raise WrapNotFoundException(m)
        self.directory = self.wrap.directory

        if self.wrap.has_wrap:
            # We have a .wrap file, source code will be placed into main
            # project's subproject_dir even if the wrap file comes from another
            # subproject.
            self.dirname = os.path.join(self.subdir_root, self.directory)
            # Check if the wrap comes from the main project.
            main_fname = os.path.join(self.subdir_root, self.wrap.basename)
            if self.wrap.filename != main_fname:
                rel = os.path.relpath(self.wrap.filename, self.source_dir)
                mlog.log('Using', mlog.bold(rel))
                # Write a dummy wrap file in main project that redirect to the
                # wrap we picked.
                with open(main_fname, 'w', encoding='utf-8') as f:
                    f.write(textwrap.dedent('''\
                        [wrap-redirect]
                        filename = {}
                        '''.format(os.path.relpath(self.wrap.filename, self.subdir_root))))
        else:
            # No wrap file, it's a dummy package definition for an existing
            # directory. Use the source code in place.
            self.dirname = self.wrap.filename
        rel_path = os.path.relpath(self.dirname, self.source_dir)

        meson_file = os.path.join(self.dirname, 'meson.build')
        cmake_file = os.path.join(self.dirname, 'CMakeLists.txt')

        if method not in ['meson', 'cmake']:
            raise WrapException('Only the methods "meson" and "cmake" are supported')

        # The directory is there and has meson.build? Great, use it.
        if method == 'meson' and os.path.exists(meson_file):
            return rel_path
        if method == 'cmake' and os.path.exists(cmake_file):
            return rel_path

        # Check if the subproject is a git submodule
        self.resolve_git_submodule()

        if os.path.exists(self.dirname):
            if not os.path.isdir(self.dirname):
                raise WrapException('Path already exists but is not a directory')
        else:
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
                    raise WrapException(f'Unknown wrap type {self.wrap.type!r}')
            try:
                self.apply_patch()
            except Exception:
                windows_proof_rmtree(self.dirname)
                raise

        # A meson.build or CMakeLists.txt file is required in the directory
        if method == 'meson' and not os.path.exists(meson_file):
            raise WrapException('Subproject exists but has no meson.build file')
        if method == 'cmake' and not os.path.exists(cmake_file):
            raise WrapException('Subproject exists but has no CMakeLists.txt file')

        return rel_path

    def check_can_download(self) -> None:
        # Don't download subproject data based on wrap file if requested.
        # Git submodules are ok (see above)!
        if self.wrap_mode is WrapMode.nodownload:
            m = 'Automatic wrap-based subproject downloading is disabled'
            raise WrapException(m)

    def resolve_git_submodule(self) -> bool:
        # Is git installed? If not, we're probably not in a git repository and
        # definitely cannot try to conveniently set up a submodule.
        if not GIT:
            return False
        # Does the directory exist? Even uninitialised submodules checkout an
        # empty directory to work in
        if not os.path.isdir(self.dirname):
            return False
        # Are we in a git repository?
        ret, out = quiet_git(['rev-parse'], Path(self.dirname).parent)
        if not ret:
            return False
        # Is `dirname` a submodule?
        ret, out = quiet_git(['submodule', 'status', '.'], self.dirname)
        if not ret:
            return False
        # Submodule has not been added, add it
        if out.startswith('+'):
            mlog.warning('git submodule might be out of date')
            return True
        elif out.startswith('U'):
            raise WrapException('git submodule has merge conflicts')
        # Submodule exists, but is deinitialized or wasn't initialized
        elif out.startswith('-'):
            if verbose_git(['submodule', 'update', '--init', '.'], self.dirname):
                return True
            raise WrapException('git submodule failed to init')
        # Submodule looks fine, but maybe it wasn't populated properly. Do a checkout.
        elif out.startswith(' '):
            verbose_git(['submodule', 'update', '.'], self.dirname)
            verbose_git(['checkout', '.'], self.dirname)
            # Even if checkout failed, try building it anyway and let the user
            # handle any problems manually.
            return True
        elif out == '':
            # It is not a submodule, just a folder that exists in the main repository.
            return False
        raise WrapException(f'Unknown git submodule output: {out!r}')

    def get_file(self) -> None:
        path = self.get_file_internal('source')
        extract_dir = self.subdir_root
        # Some upstreams ship packages that do not have a leading directory.
        # Create one for them.
        if 'lead_directory_missing' in self.wrap.values:
            os.mkdir(self.dirname)
            extract_dir = self.dirname
        shutil.unpack_archive(path, extract_dir)

    def get_git(self) -> None:
        if not GIT:
            raise WrapException(f'Git program not found, cannot download {self.packagename}.wrap via git.')
        revno = self.wrap.get('revision')
        checkout_cmd = ['-c', 'advice.detachedHead=false', 'checkout', revno, '--']
        is_shallow = False
        depth_option = []    # type: T.List[str]
        if self.wrap.values.get('depth', '') != '':
            is_shallow = True
            depth_option = ['--depth', self.wrap.values.get('depth')]
        # for some reason git only allows commit ids to be shallowly fetched by fetch not with clone
        if is_shallow and self.is_git_full_commit_id(revno):
            # git doesn't support directly cloning shallowly for commits,
            # so we follow https://stackoverflow.com/a/43136160
            verbose_git(['-c', 'init.defaultBranch=meson-dummy-branch', 'init', self.directory], self.subdir_root, check=True)
            verbose_git(['remote', 'add', 'origin', self.wrap.get('url')], self.dirname, check=True)
            revno = self.wrap.get('revision')
            verbose_git(['fetch', *depth_option, 'origin', revno], self.dirname, check=True)
            verbose_git(checkout_cmd, self.dirname, check=True)
            if self.wrap.values.get('clone-recursive', '').lower() == 'true':
                verbose_git(['submodule', 'update', '--init', '--checkout',
                             '--recursive', *depth_option], self.dirname, check=True)
            push_url = self.wrap.values.get('push-url')
            if push_url:
                verbose_git(['remote', 'set-url', '--push', 'origin', push_url], self.dirname, check=True)
        else:
            if not is_shallow:
                verbose_git(['clone', self.wrap.get('url'), self.directory], self.subdir_root, check=True)
                if revno.lower() != 'head':
                    if not verbose_git(checkout_cmd, self.dirname):
                        verbose_git(['fetch', self.wrap.get('url'), revno], self.dirname, check=True)
                        verbose_git(checkout_cmd, self.dirname, check=True)
            else:
                verbose_git(['clone', *depth_option, '--branch', revno, self.wrap.get('url'),
                             self.directory], self.subdir_root, check=True)
            if self.wrap.values.get('clone-recursive', '').lower() == 'true':
                verbose_git(['submodule', 'update', '--init', '--checkout', '--recursive', *depth_option],
                            self.dirname, check=True)
            push_url = self.wrap.values.get('push-url')
            if push_url:
                verbose_git(['remote', 'set-url', '--push', 'origin', push_url], self.dirname, check=True)

    def is_git_full_commit_id(self, revno: str) -> bool:
        result = False
        if len(revno) in (40, 64): # 40 for sha1, 64 for upcoming sha256
            result = all(ch in '0123456789AaBbCcDdEeFf' for ch in revno)
        return result

    def get_hg(self) -> None:
        revno = self.wrap.get('revision')
        hg = shutil.which('hg')
        if not hg:
            raise WrapException('Mercurial program not found.')
        subprocess.check_call([hg, 'clone', self.wrap.get('url'),
                               self.directory], cwd=self.subdir_root)
        if revno.lower() != 'tip':
            subprocess.check_call([hg, 'checkout', revno],
                                  cwd=self.dirname)

    def get_svn(self) -> None:
        revno = self.wrap.get('revision')
        svn = shutil.which('svn')
        if not svn:
            raise WrapException('SVN program not found.')
        subprocess.check_call([svn, 'checkout', '-r', revno, self.wrap.get('url'),
                               self.directory], cwd=self.subdir_root)

    def get_data(self, urlstring: str) -> T.Tuple[str, str]:
        blocksize = 10 * 1024
        h = hashlib.sha256()
        tmpfile = tempfile.NamedTemporaryFile(mode='wb', dir=self.cachedir, delete=False)
        url = urllib.parse.urlparse(urlstring)
        if url.hostname and url.hostname.endswith(WHITELIST_SUBDOMAIN):
            resp = open_wrapdburl(urlstring)
        elif WHITELIST_SUBDOMAIN in urlstring:
            raise WrapException(f'{urlstring} may be a WrapDB-impersonating URL')
        else:
            try:
                req = urllib.request.Request(urlstring, headers={'User-Agent': f'mesonbuild/{coredata.version}'})
                resp = urllib.request.urlopen(req, timeout=REQ_TIMEOUT)
            except urllib.error.URLError as e:
                mlog.log(str(e))
                raise WrapException(f'could not get {urlstring} is the internet available?')
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
            sys.stdout.flush()
            progress_bar = ProgressBar(bar_type='download', total=dlsize,
                                       desc='Downloading')
            while True:
                block = resp.read(blocksize)
                if block == b'':
                    break
                h.update(block)
                tmpfile.write(block)
                progress_bar.update(len(block))
            progress_bar.close()
            hashvalue = h.hexdigest()
        return hashvalue, tmpfile.name

    def check_hash(self, what: str, path: str, hash_required: bool = True) -> None:
        if what + '_hash' not in self.wrap.values and not hash_required:
            return
        expected = self.wrap.get(what + '_hash').lower()
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            h.update(f.read())
        dhash = h.hexdigest()
        if dhash != expected:
            raise WrapException(f'Incorrect hash for {what}:\n {expected} expected\n {dhash} actual.')

    def get_data_with_backoff(self, urlstring: str) -> T.Tuple[str, str]:
        delays = [1, 2, 4, 8, 16]
        for d in delays:
            try:
                return self.get_data(urlstring)
            except Exception as e:
                mlog.warning(f'failed to download with error: {e}. Trying after a delay...', fatal=False)
                time.sleep(d)
        return self.get_data(urlstring)

    def download(self, what: str, ofname: str, fallback: bool = False) -> None:
        self.check_can_download()
        srcurl = self.wrap.get(what + ('_fallback_url' if fallback else '_url'))
        mlog.log('Downloading', mlog.bold(self.packagename), what, 'from', mlog.bold(srcurl))
        try:
            dhash, tmpfile = self.get_data_with_backoff(srcurl)
            expected = self.wrap.get(what + '_hash').lower()
            if dhash != expected:
                os.remove(tmpfile)
                raise WrapException(f'Incorrect hash for {what}:\n {expected} expected\n {dhash} actual.')
        except WrapException:
            if not fallback:
                if what + '_fallback_url' in self.wrap.values:
                    return self.download(what, ofname, fallback=True)
                mlog.log('A fallback URL could be specified using',
                         mlog.bold(what + '_fallback_url'), 'key in the wrap file')
            raise
        os.rename(tmpfile, ofname)

    def get_file_internal(self, what: str) -> str:
        filename = self.wrap.get(what + '_filename')
        if what + '_url' in self.wrap.values:
            cache_path = os.path.join(self.cachedir, filename)

            if os.path.exists(cache_path):
                self.check_hash(what, cache_path)
                mlog.log('Using', mlog.bold(self.packagename), what, 'from cache.')
                return cache_path

            os.makedirs(self.cachedir, exist_ok=True)
            self.download(what, cache_path)
            return cache_path
        else:
            path = Path(self.wrap.filesdir) / filename

            if not path.exists():
                raise WrapException(f'File "{path}" does not exist')
            self.check_hash(what, path.as_posix(), hash_required=False)

            return path.as_posix()

    def apply_patch(self) -> None:
        if 'patch_filename' in self.wrap.values and 'patch_directory' in self.wrap.values:
            m = f'Wrap file {self.wrap.basename!r} must not have both "patch_filename" and "patch_directory"'
            raise WrapException(m)
        if 'patch_filename' in self.wrap.values:
            path = self.get_file_internal('patch')
            try:
                shutil.unpack_archive(path, self.subdir_root)
            except Exception:
                with tempfile.TemporaryDirectory() as workdir:
                    shutil.unpack_archive(path, workdir)
                    self.copy_tree(workdir, self.subdir_root)
        elif 'patch_directory' in self.wrap.values:
            patch_dir = self.wrap.values['patch_directory']
            src_dir = os.path.join(self.wrap.filesdir, patch_dir)
            if not os.path.isdir(src_dir):
                raise WrapException(f'patch directory does not exist: {patch_dir}')
            self.copy_tree(src_dir, self.dirname)

    def copy_tree(self, root_src_dir: str, root_dst_dir: str) -> None:
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
