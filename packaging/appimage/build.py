#!/usr/bin/env python3

# Copyright 2020 Daniel Mensinger

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import argparse
import shutil
import hashlib
import urllib.request
import subprocess
import multiprocessing
import re
import time
import stat
import tempfile
import textwrap
from pathlib import Path

import typing as T

appimage_dir = Path(__file__).resolve().parent
root_dir = appimage_dir.parents[1]
timers = []

def as_string(x) -> str:
    if x is None:
        return None
    if isinstance(x, Path):
        return x.resolve().as_posix()
    elif not isinstance(x, str):
        return str(x)
    return x

def as_string_rel(x) -> str:
    if isinstance(x, Path):
        try:
            return x.resolve().relative_to(root_dir).as_posix()
        except ValueError:
            return x.resolve().as_posix()
    return as_string(x)

def run_checked(args, cwd=None, env=None, short: bool = False, quiet: bool = False) -> None:
    cwd_str = as_string(cwd)
    args_abs = [as_string(x) for x in args]
    args_rel = [as_string_rel(x) for x in args]

    sys.stdout.flush()
    sys.stderr.flush()

    if short:
        print(f'\x1b[32mRunning \x1b[0;1m{" ".join(args_rel)}\x1b[0;33m\x1b[0m')
    elif not quiet:
        print(f'\n\n\x1b[32mRunning \x1b[0;1m{" ".join(args_rel)}\x1b[0;33m in \x1b[1;35m{as_string_rel(cwd)}\x1b[0m')
    try:
        rc = subprocess.run(args_abs, cwd=cwd_str, env=env)
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        rc = None
    finally:
        if rc is None or rc.returncode != 0:
            print('''\x1b[31;1m
                 _________________ ___________
                |  ___| ___ \ ___ \  _  | ___ \\
                | |__ | |_/ / |_/ / | | | |_/ /
                |  __||    /|    /| | | |    /
                | |___| |\ \| |\ \\\\ \_/ / |\ \\
                \____/\_| \_\_| \_|\___/\_| \_|\x1b[0m
            ''')
            sys.stdout.flush()
            sys.stderr.flush()
            raise RuntimeError('Process Failed ({})'.format(args))


def timed_code(func):
    def wrapper(*args, **kwargs):
        global timers
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        timers += [(func.__name__, end - start)]
    return wrapper

class SourceBase:
    def __init__(self, url: str, filename: str, sha256sum: str, dirname: str, strip: int = 1):
        self.url = url
        self.filename = filename
        self.dirname = dirname
        self.sha256sum = sha256sum
        self.strip = strip

    def check_hash(self, out_file: Path) -> bool:
        curr_hash = hashlib.sha256(out_file.read_bytes())
        if curr_hash.hexdigest() != self.sha256sum:
            print(f'Hash validation for {self.filename} failed')
            return False
        return True

    def download(self, dest: Path) -> bool:
        out_file = dest / self.filename
        if not out_file.exists():
            urllib.request.urlretrieve(self.url, str(out_file))
        return self.check_hash(out_file)

    def extract(self, dest: Path) -> None:
        raise RuntimeError('Not implemented')

class ArchiveSource(SourceBase):
    def extract(self, dest: Path) -> None:
        out_file = dest / self.filename
        out_dir = dest.parent / self.dirname
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir()
        run_checked([
            'tar',
            '-xf', out_file,
            f'--strip-components={self.strip}',
            '-C', out_dir
        ], quiet=True)

class AppImageSource(SourceBase):
    def extract(self, dest: Path) -> None:
        out_file = dest / self.filename
        st = os.stat(out_file.as_posix())
        os.chmod(out_file.as_posix(), st.st_mode | stat.S_IEXEC)

SOURCES = {
    'python': ArchiveSource(
        'https://www.python.org/ftp/python/3.9.6/Python-3.9.6.tgz',
        'python_3_9_6.tar.gz',
        'd0a35182e19e416fc8eae25a3dcd4d02d4997333e4ad1f2eee6010aadc3fe866',
        'python',
    ),
    'ninja': ArchiveSource(
        'https://github.com/ninja-build/ninja/archive/v1.10.2.tar.gz',
        'ninja_1_10_2.tar.gz',
        'ce35865411f0490368a8fc383f29071de6690cbadc27704734978221f25e2bed',
        'ninja',
    ),
    'cmake': ArchiveSource(
        'https://github.com/Kitware/CMake/releases/download/v3.20.5/cmake-3.20.5.tar.gz',
        'cmake_3_20_5.tar.gz',
        '12c8040ef5c6f1bc5b8868cede16bb7926c18980f59779e299ab52cbc6f15bb0',
        'cmake',
    ),
    'pkgconf': ArchiveSource(
        'https://github.com/pkgconf/pkgconf/archive/refs/tags/pkgconf-1.7.4.tar.gz',
        'pkgconf_1_7_4.tar.gz',
        '2828dcdef88098748c306281d64a630b4ccd0703b1d92b532c31411e531d3088',
        'pkgconf',
    ),
    'appimagekit': AppImageSource(
        'https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage',
        'appimagetool-x86_64.AppImage',
        'df3baf5ca5facbecfc2f3fa6713c29ab9cefa8fd8c1eac5d283b79cab33e4acb',
        'appimagetool',
    ),
}


class AppImageBuilder:
    def __init__(self) -> None:
        self.build_dir = root_dir / 'appimage'
        self.app_dir = self.build_dir / 'AppDir'
        self.download_dir = self.build_dir / 'downloads'
        self.wrappers_bld_dir = self.build_dir / 'wrappers'
        self.runtime_bld_dir = self.build_dir / 'runtime'
        self.runtime_exe = self.runtime_bld_dir / 'runtime'

        self.meson = root_dir / 'meson.py'
        self.python = self.app_dir / 'usr' / 'bin' / 'python3'
        self.ninja = self.app_dir / 'usr' / 'bin' / 'ninja'
        self.cmake = self.app_dir / 'usr' / 'bin' / 'cmake'
        self.patchelf = shutil.which('patchelf')
        self.appimagetool = self.download_dir / 'appimagetool-x86_64.AppImage'
        self.env = os.environ.copy()
        self.nproc = multiprocessing.cpu_count()

        if not self.patchelf:
            raise RuntimeError('Unable to find patchelf')

    @timed_code
    def install_python(self) -> None:
        python_dir = self.build_dir / SOURCES['python'].dirname
        run_checked([
            './configure',
            '--prefix=/usr',
            '--with-computed-gotos',
            '--enable-ipv6',
            '--enable-optimizations',
            '--with-lto',
            '--without-ensurepip',
        ], cwd=python_dir, env=self.env)
        run_checked(['make', '-j', self.nproc], cwd=python_dir, env=self.env)
        run_checked(['make', 'install'], cwd=python_dir, env=self.env)
        run_checked([self.python, '-E', '-m', 'ensurepip'], cwd=self.app_dir, env=self.env)

        # Create symlink
        raw_python = self.app_dir / 'usr' / 'bin' / 'python'
        raw_python.symlink_to(self.python.resolve().name)

    @timed_code
    def install_ninja(self) -> None:
        ninja_dir = self.build_dir / SOURCES['ninja'].dirname
        run_checked([self.python, './configure.py', '--bootstrap'], cwd=ninja_dir, env=self.env)
        shutil.copy2(ninja_dir / 'ninja', self.app_dir / 'usr' / 'bin' / 'ninja')

    @timed_code
    def install_meson(self) -> None:
        run_checked([
            self.python, '-m', 'pip',
            'install',
            '--prefix', self.app_dir / 'usr',
            '--ignore-installed',
            '.',
        ], cwd=root_dir, env=self.env)

        # Use our meson.py script instead of the broken stuff setuptools generates
        meson_exe = self.app_dir / 'usr' / 'bin' / 'meson'
        meson_py = root_dir / 'meson.py'
        meson_exe.unlink()
        shutil.copy2(meson_py, meson_exe)

    @timed_code
    def install_cmake(self) -> None:
        cmake_dir = self.build_dir / SOURCES['cmake'].dirname
        run_checked([
            './bootstrap',
            '--prefix=/usr',
            '--no-system-libs',
            '--no-qt-gui',
            f'--parallel={self.nproc}',
            '--',
            '-DCMAKE_BUILD_TYPE=RELEASE',
            '-DCMAKE_USE_OPENSSL=OFF',
            '-DBUILD_CursesDialog=OFF',
        ], cwd=cmake_dir, env=self.env)
        run_checked(['make', '-j', self.nproc], cwd=cmake_dir, env=self.env)
        run_checked(['make', 'install'], cwd=cmake_dir, env=self.env)

    @timed_code
    def pip_install(self, what: str) -> None:
        run_checked([
            self.python, '-m', 'pip',
            'install',
            '--prefix', self.app_dir / 'usr',
            '--ignore-installed',
            what,
        ])

    @timed_code
    def install_pkgconf(self) -> None:
        pkg_config_dir = self.build_dir / SOURCES['pkgconf'].dirname
        run_checked([self.meson, 'build', '-Dtests=false', '-Dprefix=/usr'], cwd=pkg_config_dir, env=self.env)
        run_checked(['ninja', '-C', 'build'], cwd=pkg_config_dir, env=self.env)
        run_checked(['ninja', '-C', 'build', 'install'], cwd=pkg_config_dir, env=self.env)

    @timed_code
    def build_wrappers(self) -> None:
        # Build AppRun binaries
        apprun_dir = appimage_dir / 'wrappers'
        run_checked([self.meson, self.wrappers_bld_dir], cwd=apprun_dir, env=self.env)
        run_checked(['ninja'], cwd=self.wrappers_bld_dir, env=self.env)
        run_checked(['ninja', 'install'], cwd=self.wrappers_bld_dir, env=self.env)

    @timed_code
    def build_runtime(self) -> None:
        # Build our custom AppImage runtime
        runtime_dir = appimage_dir / 'runtime'
        run_checked([self.python, self.meson, '--wrap-mode=forcefallback', self.runtime_bld_dir], cwd=runtime_dir, env=self.env)
        run_checked(['ninja'], cwd=self.runtime_bld_dir, env=self.env)

    @timed_code
    def cleanup(self) -> None:
        to_remove = []
        to_remove += [x for x in self.app_dir.glob('**/*.a')]
        to_remove += [x for x in self.app_dir.glob('**/*.pc')]
        to_remove += [x for x in self.app_dir.glob('**/*.rst')]
        to_remove += [x for x in self.app_dir.glob('**/Help/**/*.txt')]
        to_remove += [x for x in self.app_dir.glob('**/Help/**/*.png')]
        to_remove += [x for x in self.app_dir.glob('**/bin/2to3*')]
        to_remove += [x for x in self.app_dir.glob('**/bin/easy*')]
        to_remove += [x for x in self.app_dir.glob('**/bin/idle*')]
        to_remove += [x for x in self.app_dir.glob('**/bin/pip*')]
        to_remove += [x for x in self.app_dir.glob('**/bin/python3*-config*')]
        to_remove += [x for x in self.app_dir.glob('**/bin/pydoc*')]
        to_remove += [x for x in self.app_dir.glob('**/bin/cpack')]
        to_remove += [x for x in self.app_dir.glob('**/bin/ctest')]
        to_remove += [x for x in self.app_dir.glob('**/site-packages/pip*')]
        to_remove += [x for x in self.app_dir.glob('usr/doc')]
        to_remove += [x for x in self.app_dir.glob('usr/include')]
        to_remove += [x for x in self.app_dir.glob('usr/share/vim*')]
        to_remove += [x for x in self.app_dir.glob('usr/share/man*')]
        to_remove += [x for x in self.app_dir.glob('usr/share/doc*')]
        to_remove += [x for x in self.app_dir.glob('usr/share/emacs*')]
        to_remove += [x for x in self.app_dir.glob('usr/share/ac*')]

        # all test dirs
        to_remove += [x for x in self.app_dir.glob('**/lib/python*/**/test')]
        to_remove += [x for x in self.app_dir.glob('**/lib/python*/**/tests')]

        def rm_module(mod: str) -> None:
            nonlocal to_remove
            to_remove += [x for x in self.app_dir.glob('**/lib/python*/{}*'.format(mod))]
            to_remove += [x for x in self.app_dir.glob('**/lib/python*/_{}*'.format(mod))]
            to_remove += [x for x in self.app_dir.glob('**/lib-dynload/{}*.so'.format(mod))]
            to_remove += [x for x in self.app_dir.glob('**/lib-dynload/_{}*.so'.format(mod))]

        # Remove big modules we don't use/need
        rm_module('tkinter')
        rm_module('unittest')
        rm_module('lib2to3')
        rm_module('ensurepip')
        rm_module('idlelib')
        rm_module('pydoc')

        for i in to_remove:
            print('Deleting {}'.format(i))
            if i.is_dir():
                shutil.rmtree(str(i))
            else:
                i.unlink()

        # Remove empty directories
        while True:
            to_remove = []
            for i in self.app_dir.glob('**'):
                if not [x for x in i.iterdir()] :
                    to_remove += [i]

            if not to_remove:
                break

            for i in to_remove:
                print('Deleting empty dir {}'.format(i))
                shutil.rmtree(str(i))

    @timed_code
    def move_libs_to_bin(self) -> None:
        # Move the libraries next to the binaries so we don't need to
        # mess with LD_LIBRARY_PATH
        usr_lib = self.app_dir / 'usr' / 'lib'
        usr_bin = self.app_dir / 'usr' / 'bin'
        targets = [x for x in usr_lib.glob('*.so')]
        for i in targets:
            shutil.move(i, usr_bin)

    @timed_code
    def copy_libs(self) -> None:
        # 1st: Search all *.so and executables
        targets = []
        targets += [x for x in self.app_dir.glob('**/*.so*')]
        targets += [x for x in self.app_dir.glob('**/bin/*')]
        targets = [x for x in targets if x.is_file() and not x.is_symlink()]

        path_reg = re.compile(r'=>\s*([^ ]+)')
        libs_set: T.Set[Path] = set()

        # 2nd: use `ldd` to extract the libraries
        for i in targets:
            res = subprocess.run(['ldd', str(i)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            lines = res.stdout.decode().split('\n')
            for l in lines:
                m = path_reg.search(l)
                if not m:
                    continue
                libs_set.add(Path(m.group(1)))

        # 3rd: detect ld-linux.so and handle it seperately
        ld_so = Path()
        def extract_ld(libp: Path) -> bool:
            nonlocal ld_so
            if libp.name.startswith('ld'):
                ld_so = libp
                return True
            return False

        libs = sorted(libs_set)
        libs = [x for x in libs if not extract_ld(x)]
        dest = self.app_dir / 'usr' / 'lib'

        # 4th: Copy the remaining libraries to AppDir/usr/bin
        for p in libs:
            print('Copying {}'.format(p))
            shutil.copy2(p, dest)

        # 5th: Copy ld-linux.so
        print('ld-linux is {}'.format(ld_so))
        shutil.copy2(ld_so, dest / 'ld-linux.so')

    @timed_code
    def copy_metadata(self) -> None:
        icon_src = root_dir / 'graphics' / 'meson_logo_big.png'
        icon_dst = self.app_dir / 'meson.png'
        metainfo_dir = self.app_dir / 'usr' / 'share' / 'metainfo'
        metainfo_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(appimage_dir / 'meson.desktop', self.app_dir)
        shutil.copy2(appimage_dir / 'meson.appdata.xml', metainfo_dir)
        shutil.copy2(icon_src, icon_dst)

    @timed_code
    def rebuild_pycache(self) -> None:
        # Rebuild the pycache with --invalidation-mode unchecked-hash because
        # the AppImage will mess up the timestamps and thus invalidate the current
        # timestamp based pycache
        dirs: T.List[str] = []
        for i in self.app_dir.glob('**/__pycache__'):
            dirs += [i.parent.resolve().as_posix()]
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as fd:
            fd.write('\n'.join(dirs))
            fd.flush()
            run_checked([
                self.python,
                '-m', 'compileall',
                '--invalidation-mode', 'unchecked-hash',
                '-l', '-f',
                '-i', fd.name,
            ])

    @timed_code
    def process_binaries(self) -> None:
        binaries: T.List[Path] = []
        binaries += [x for x in self.app_dir.glob('**/bin/*')]
        binaries += [x for x in self.app_dir.glob('**/*.so')]
        binaries += [x for x in self.app_dir.glob('**/*.so.*')]
        binaries = [x for x in binaries if not x.read_bytes().startswith(b'#!')]
        binaries = [x for x in binaries if x.name != 'ld-linux.so']
        binaries = sorted(set(binaries))
        for i in binaries:
            print(f' - stripping and setting RPATH for {i}')
            relpath = os.path.relpath(self.app_dir / "usr" / "lib", i.parent)
            run_checked([self.env['STRIP'], i], env=self.env, short=True)
            run_checked([self.patchelf, '--set-rpath', f'$ORIGIN/{relpath}', i], env=self.env, short=True)

    @timed_code
    def build_appimage(self, output: str, delayed_packageing: bool) -> None:
        apprun = self.app_dir / 'AppRun'
        apprun.symlink_to(Path('fakebin') / 'meson')
        args = [self.appimagetool, '-n', self.app_dir, '--runtime-file', self.runtime_exe, output]
        args = ['./' + x.resolve().relative_to(self.build_dir).as_posix() if isinstance(x, Path) else x for x in args]
        if delayed_packageing:
            args_str = ' '.join([str(x) for x in args])
            out_file = self.build_dir / 'package.sh'
            out_file.write_text(
                encoding='utf-8',
                data=textwrap.dedent(
                    f'''\
                        #!/bin/sh

                        cd "$(dirname "$0")"

                        {args_str}
                    '''
                )
            )
            st = os.stat(out_file.as_posix())
            os.chmod(out_file.as_posix(), st.st_mode | stat.S_IEXEC)
        else:
            run_checked(args, cwd=root_dir, env=self.env)

    def run(self) -> int:
        parser = argparse.ArgumentParser(description='builds the meson AppImage')
        parser.add_argument('-o', '--output', type=str, help='Output filename', default='meson.runtime')
        parser.add_argument('-d', '--delayed-packageing', action='store_true', help='Write the packaging command to a script instead of executing it directly')
        args = parser.parse_args()

        if not self.build_dir.exists():
            self.build_dir.mkdir()

        for d in self.build_dir.iterdir():
            if d.name == 'downloads':
                continue
            if d.is_dir():
                shutil.rmtree(d)
            else:
                d.unlink()

        if self.app_dir.exists():
            shutil.rmtree(self.app_dir)
        self.app_dir.mkdir()

        if not self.download_dir.exists():
            self.download_dir.mkdir()

        self.env['DESTDIR'] = str(self.app_dir)
        #self.env['CFLAGS'] = '-static-libstdc++ -static-libgcc'
        #self.env['CXXFLAGS'] = '-static-libstdc++ -static-libgcc'
        self.env['PATH'] = str(self.app_dir / 'usr' / 'bin') + ':' + self.env['PATH']
        self.env['PYTHONHOME'] = str(self.app_dir / 'usr')

        ccache = shutil.which('ccache') or ''
        if ccache:
            ccache += ' '

        if 'CC' not in self.env:
            self.env['CC'] = f'{ccache}gcc'
        if 'CXX' not in self.env:
            self.env['CXX'] = f'{ccache}g++'
        if 'STRIP' not in self.env:
            self.env['STRIP'] = 'strip'

        print('Downloading files...')
        for k, v in SOURCES.items():
            res = v.download(self.download_dir)
            print(' - {}: {}'.format(k, res))
            if not res:
                return 1

        print('Extracting sources...')
        for k, v in SOURCES.items():
            v.extract(self.download_dir)
            print(' - {}: DONE'.format(k))

        self.install_python()
        self.install_ninja()
        self.install_meson()
        #self.install_cmake()
        self.install_pkgconf()
        self.pip_install('tqdm')

        self.cleanup()
        self.rebuild_pycache()
        self.copy_libs()
        self.copy_metadata()
        self.build_wrappers()
        self.build_runtime()
        self.process_binaries()
        self.build_appimage(args.output, args.delayed_packageing)


        print(f'''\n\n\x1b[32;1m
                        ______ _____ _   _  _____
                        |  _  \  _  | \ | ||  ___|
                        | | | | | | |  \| || |__
                        | | | | | | | . ` ||  __|
                        | |/ /\ \_/ / |\  || |___
                        |___/  \___/\_| \_/\____/\x1b[0m

            `{args.output}` has been created in the project root

            Build dir: {self.build_dir}

            Timers:
        ''')

        for i in timers:
            print('              - {:<24} -- {:.2f}s'.format(i[0], i[1]))

        return 0

if __name__ == '__main__':
    sys.exit(AppImageBuilder().run())
