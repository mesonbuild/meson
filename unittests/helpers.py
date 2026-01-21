# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

from __future__ import annotations
import subprocess
import os
import shutil
import unittest
import functools
import re
import typing as T
import zipfile
from pathlib import Path
from contextlib import contextmanager
from unittest import mock

from mesonbuild.compilers import compiler_from_language
from mesonbuild.mesonlib import (
    MachineChoice, is_osx, is_cygwin, OrderedSet, EnvironmentException,
)
from mesonbuild.options import OptionKey
from run_tests import get_fake_env

if T.TYPE_CHECKING:
    from typing_extensions import ParamSpec

    from mesonbuild.compilers import Compiler
    from mesonbuild.compilers.compilers import CompilerDict, Language

    P = ParamSpec('P')
    R = T.TypeVar('R')


IS_CI = os.environ.get('MESON_CI_JOBNAME', 'thirdparty') != 'thirdparty'


class _CompilerSkip:

    """Helper class for skipping based on whether the C compiler supports a
    compiler option.

    Known limits:
      - only checks a C compiler
      - only checks the host machine
    """

    def __init__(self) -> None:
        self._env = get_fake_env()
        self._cache: CompilerDict = {}

    def _compiler(self, lang: Language) -> T.Optional[Compiler]:
        try:
            return self._cache[lang]
        except KeyError:
            try:
                comp = compiler_from_language(self._env, lang, MachineChoice.HOST)
            except EnvironmentException:
                comp = None
            self._cache[lang] = comp
            return comp

    def require_base_opt(self, feature: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
        """Skip tests if the compiler does not support a given base option.

        for example, ICC doesn't currently support b_sanitize.
        """
        def actual(f: T.Callable[P, R]) -> T.Callable[P, R]:
            key = OptionKey(feature)

            @functools.wraps(f)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                comp = self._compiler('c')
                assert comp is not None
                if key not in comp.base_options:
                    raise unittest.SkipTest(
                        f'{feature} not available with {comp.id}')

                return f(*args, **kwargs)
            return wrapped
        return actual

    def require_language(self, lang: Language) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
        def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
            @functools.wraps(func)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                if not self._compiler(lang):
                    raise unittest.SkipTest(f'No {lang} compiler found.')
                return func(*args, **kwargs)
            return wrapped
        return wrapper


_compiler = _CompilerSkip()
skip_if_not_base_option = _compiler.require_base_opt
skip_if_not_language = _compiler.require_language


class _PkgConfigSkip:

    def __init__(self) -> None:
        self.pkgconf = shutil.which('pkg-config') or shutil.which('pkgconf')
        self.depcache: T.Dict[str, bool] = {}

    def require_pkgconf(self, f: T.Callable[P, R]) -> T.Callable[P, R]:
        '''
        Skip this test if no pkg-config is found, unless we're on CI.
        This allows users to run our test suite without having
        pkg-config installed on, f.ex., macOS, while ensuring that our CI does not
        silently skip the test because of misconfiguration.

        Note: Yes, we provide pkg-config even while running Windows CI
        '''
        if IS_CI:
            return f

        @functools.wraps(f)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if self.pkgconf is None:
                raise unittest.SkipTest('pkg-config not found')
            return f(*args, **kwargs)
        return wrapped

    def _has_dep(self, depname: str) -> bool:
        try:
            return self.depcache[depname]
        except KeyError:
            found = subprocess.call([self.pkgconf, '--exists', depname]) == 0
            self.depcache[depname] = found
            return found

    def require_dep(self, depname: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
        '''
        Skip this test if the given pkg-config dep is not found, unless we're on CI.
        '''
        def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
            if IS_CI:
                return func

            @functools.wraps(func)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                if self.pkgconf is None:
                    raise unittest.SkipTest('pkg-config not found')
                if not self._has_dep(depname):
                    raise unittest.SkipTest(f'pkg-config dependency {depname} not found.')
                return func(*args, **kwargs)
            return wrapped
        return wrapper


_pkgconf = _PkgConfigSkip()
skipIfNoPkgconfig = _pkgconf.require_pkgconf
skipIfNoPkgconfigDep = _pkgconf.require_dep


class _ExecutableHelper:

    def __init__(self) -> None:
        self._cache: T.Dict[str, bool] = {}

    def _exists(self, name: str) -> bool:
        try:
            return self._cache[name]
        except KeyError:
            found = shutil.which(name) is not None
            self._cache[name] = found
            return found

    def require_cmake(self, f: T.Callable[P, R]) -> T.Callable[P, R]:
        '''
        Skip this test if no cmake is found, unless we're on CI.
        This allows users to run our test suite without having
        cmake installed on, f.ex., macOS, while ensuring that our CI does not
        silently skip the test because of misconfiguration.
        '''
        if IS_CI:
            return f

        @functools.wraps(f)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if not self._exists('cmake'):
                raise unittest.SkipTest('cmake not found')
            return f(*args, **kwargs)
        return wrapped

    def require_executable(self, exename: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
        '''
        Skip this test if the given executable is not found.
        '''
        def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
            @functools.wraps(func)
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
                if not self._exists(exename):
                    raise unittest.SkipTest(exename + ' not found')
                return func(*args, **kwargs)
            return wrapped
        return wrapper


_exe = _ExecutableHelper()
skip_if_no_cmake = _exe.require_cmake
skipIfNoExecutable = _exe.require_executable


def skip_if_env_set(key: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    '''
    Skip a test if a particular env is set, except when running under CI
    '''
    def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if not IS_CI and key in os.environ:
                raise unittest.SkipTest(f'Env var {key!r} set, skipping')
            with mock.patch.dict(os.environ):
                os.environ.pop(key, None)
                return func(*args, **kwargs)
        return wrapped
    return wrapper


def is_tarball() -> bool:
    return not os.path.isdir('docs')


@contextmanager
def chdir(path: str) -> T.Iterator[None]:
    curdir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(curdir)


def get_dynamic_section_entry(fname: str, entry: str) -> T.Optional[str]:
    if is_cygwin() or is_osx():
        raise unittest.SkipTest('Test only applicable to ELF platforms')

    try:
        raw_out = subprocess.check_output(['readelf', '-d', fname],
                                          encoding='utf-8', universal_newlines=True)
    except FileNotFoundError:
        # FIXME: Try using depfixer.py:Elf() as a fallback
        raise unittest.SkipTest('readelf not found')
    pattern = re.compile(entry + r': \[(.*?)\]')
    for line in raw_out.split('\n'):
        m = pattern.search(line)
        if m is not None:
            return str(m.group(1))
    return None # The file did not contain the specified entry.


def get_soname(fname: str) -> T.Optional[str]:
    return get_dynamic_section_entry(fname, 'soname')


def get_rpath(fname: str) -> T.Optional[str]:
    raw = get_dynamic_section_entry(fname, r'(?:rpath|runpath)')
    # Get both '' and None here
    if not raw:
        return None
    # nix/nixos adds a bunch of stuff to the rpath out of necessity that we
    # don't check for, so clear those
    final = ':'.join([e for e in raw.split(':') if not e.startswith('/nix')])
    # If we didn't end up anything but nix paths, return None here
    if not final:
        return None
    return final


def get_classpath(fname: str) -> T.Optional[str]:
    with zipfile.ZipFile(fname) as zip:
        with zip.open('META-INF/MANIFEST.MF') as member:
            contents = member.read().decode().strip()
    lines: T.List[str] = []
    for line in contents.splitlines():
        if line.startswith(' '):
            # continuation line
            lines[-1] += line[1:]
        else:
            lines.append(line)
    manifest = {
        k.lower(): v.strip() for k, v in [l.split(':', 1) for l in lines]
    }
    return manifest.get('class-path')


def get_path_without_cmd(cmd: str, path: str) -> str:
    pathsep = os.pathsep
    paths = OrderedSet([Path(p).resolve() for p in path.split(pathsep)])
    while True:
        full_path = shutil.which(cmd, path=path)
        if full_path is None:
            break
        dirname = Path(full_path).resolve().parent
        paths.discard(dirname)
        path = pathsep.join([str(p) for p in paths])
    return path


def xfail_if_jobname(name: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    if os.environ.get('MESON_CI_JOBNAME') == name:
        return unittest.expectedFailure

    def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
        return func
    return wrapper
