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

from mesonbuild.compilers import detect_c_compiler, compiler_from_language
from mesonbuild.mesonlib import (
    MachineChoice, is_osx, is_cygwin, EnvironmentException, MachineChoice,
    OrderedSet
)
from mesonbuild.options import OptionKey
from run_tests import get_fake_env

if T.TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec('P')
    R = T.TypeVar('R')


def is_ci() -> bool:
    return os.environ.get('MESON_CI_JOBNAME', 'thirdparty') != 'thirdparty'


def skip_if_not_base_option(feature: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    """Skip tests if The compiler does not support a given base option.

    for example, ICC doesn't currently support b_sanitize.
    """
    def actual(f: T.Callable[P, R]) -> T.Callable[P, R]:
        @functools.wraps(f)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            env = get_fake_env()
            cc = detect_c_compiler(env, MachineChoice.HOST)
            key = OptionKey(feature)
            if key not in cc.base_options:
                raise unittest.SkipTest(
                    f'{feature} not available with {cc.id}')
            return f(*args, **kwargs)
        return wrapped
    return actual


def skipIfNoPkgconfig(f: T.Callable[P, R]) -> T.Callable[P, R]:
    '''
    Skip this test if no pkg-config is found, unless we're on CI.
    This allows users to run our test suite without having
    pkg-config installed on, f.ex., macOS, while ensuring that our CI does not
    silently skip the test because of misconfiguration.

    Note: Yes, we provide pkg-config even while running Windows CI
    '''
    @functools.wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        if not is_ci() and shutil.which('pkg-config') is None:
            raise unittest.SkipTest('pkg-config not found')
        return f(*args, **kwargs)
    return wrapped


def skipIfNoPkgconfigDep(depname: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    '''
    Skip this test if the given pkg-config dep is not found, unless we're on CI.
    '''
    def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if not is_ci() and shutil.which('pkg-config') is None:
                raise unittest.SkipTest('pkg-config not found')
            if not is_ci() and subprocess.call(['pkg-config', '--exists', depname]) != 0:
                raise unittest.SkipTest(f'pkg-config dependency {depname} not found.')
            return func(*args, **kwargs)
        return wrapped
    return wrapper


def skip_if_no_cmake(f: T.Callable[P, R]) -> T.Callable[P, R]:
    '''
    Skip this test if no cmake is found, unless we're on CI.
    This allows users to run our test suite without having
    cmake installed on, f.ex., macOS, while ensuring that our CI does not
    silently skip the test because of misconfiguration.
    '''
    @functools.wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        if not is_ci() and shutil.which('cmake') is None:
            raise unittest.SkipTest('cmake not found')
        return f(*args, **kwargs)
    return wrapped


def skip_if_not_language(lang: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                compiler_from_language(get_fake_env(), lang, MachineChoice.HOST)
            except EnvironmentException:
                raise unittest.SkipTest(f'No {lang} compiler found.')
            return func(*args, **kwargs)
        return wrapped
    return wrapper


def skip_if_env_set(key: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    '''
    Skip a test if a particular env is set, except when running under CI
    '''
    def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if key in os.environ and not is_ci():
                raise unittest.SkipTest(f'Env var {key!r} set, skipping')
            with mock.patch.dict(os.environ):
                os.environ.pop(key, None)
                return func(*args, **kwargs)
        return wrapped
    return wrapper


def skipIfNoExecutable(exename: str) -> T.Callable[[T.Callable[P, R]], T.Callable[P, R]]:
    '''
    Skip this test if the given executable is not found.
    '''
    def wrapper(func: T.Callable[P, R]) -> T.Callable[P, R]:
        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if shutil.which(exename) is None:
                raise unittest.SkipTest(exename + ' not found')
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
