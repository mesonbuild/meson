# Copyright 2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
import shlex
from collections import OrderedDict
from pathlib import Path

from . import MesonException, version_compare

import typing as T


class PkgConfigException(MesonException):
    pass

class RequiredVersion:
    def __init__(self, name: str, wanted: str):
        self.name = name
        self.wanted = wanted

class Package:
    def __init__(self, repo: 'Repository', name: str, filename: Path, sysroot: Path) -> None:
        self.repo = repo
        self.pkgname = name
        self.filename = filename
        self.sysroot = sysroot

        self.globals = {'pc_sysrootdir': sysroot.as_posix() if sysroot else '/',
                        'pcfiledir': self.filename.parent.as_posix()}
        self.variables = self.globals.copy()
        self.raw_variables: OrderedDict[str, str] = OrderedDict()
        self.name = ''
        self.description = ''
        self.version = ''
        self.url = ''
        self.requires_private: T.List[Package] = []
        self.requires: T.List[Package] = []
        self.conflicts: T.List[RequiredVersion] = []
        self.libs_private: T.List[str] = []
        self.libs: T.List[str] = []
        self.cflags: T.List[str] = []

        self._parse()
        self._check_conflicts()

    def _parse(self) -> None:
        requires = []
        requires_private = []
        for line in self._readlines():
            key_len = next((i for i, ch in enumerate(line) if ch in ['=', ':']), None)
            if not key_len:
                continue
            key = line[:key_len].strip()
            raw_value = line[key_len+1:].strip()
            value = self._expand(raw_value, self.variables)
            if line[key_len] == '=':
                value = self._unquote(value)
                raw_value = self._unquote(raw_value)
                if key == 'prefix':
                    value = self._prepend_sysroot(value)
                    raw_value = self._prepend_sysroot(raw_value)
                self.variables[key] = value
                self.raw_variables[key] = raw_value
            elif key == 'Name':
                self.name = value
            elif key == 'Description':
                self.description = value
            elif key == 'Version':
                self.version = value
            elif key == 'URL':
                self.url = value
            elif key == 'Requires.private':
                requires_private = self._parse_requires(value)
            elif key == 'Requires':
                requires = self._parse_requires(value)
            elif key == 'Conflicts':
                self.conflicts = self._parse_requires(value)
            elif key == 'Libs.private':
                self.libs_private = self._parse_args(value)
            elif key == 'Libs':
                self.libs = self._parse_args(value)
            elif key == 'Cflags' or key == 'CFlags':
                self.cflags = self._parse_args(value)
        self.requires = self._lookup_requires(requires)
        self.requires_private = self._lookup_requires(requires_private)

    def _unquote(self, value: str) -> str:
        # pkg-config uses g_shell_unquote(), this trick seems close enough.
        if value and value[0] in {'\'', '"'}:
            try:
                value = self._split_args(value)[0]
            except ValueError:
                pass
        return value

    def _parse_args(self, value: str) -> T.List[str]:
        args = []
        for a in self._split_args(value):
            # Canonicalize '-I /foo' to '-I/foo'
            if a.startswith('-I') or a.startswith('-L'):
                a = a[:2] + a[2:].lstrip()
            args.append(a)
        return args

    def _split_args(self, value: str) -> T.List[str]:
        # We don't use mesonlib.split_args() here because it does platform
        # specific escaping. pkg-config uses g_shell_parse_argv() that does
        # "UNIX98 /bin/sh" format. Using mesonlib.split_args() here would make
        # CI fail on mingw64.
        return shlex.split(value)

    def _prepend_sysroot(self, path: str) -> str:
        if not self.sysroot:
            return path
        p = Path(path)
        p = p.relative_to(p.anchor)
        return Path(self.sysroot, p).as_posix()

    def _parse_requires(self, content: str) -> T.List[RequiredVersion]:
        SEPARATORS = ' ,'
        OPERATORS = '<>=!'

        STATE_NAME = 1
        STATE_OPERATOR = 2
        STATE_VERSION = 3

        packages = []
        name = ''
        op = ''
        version = ''

        def process_package() -> None:
            wanted = op + version
            packages.append(RequiredVersion(name, wanted))

        start = 0
        state = STATE_NAME
        for i, c in enumerate(itertools.chain(content, ' ')):
            if state == STATE_NAME:
                if c in SEPARATORS:
                    if not name:
                        name = content[start:i]
                    start = i + 1
                elif c in OPERATORS:
                    state = STATE_OPERATOR
                    if not name:
                        name = content[start:i]
                    start = i
                elif name:
                    process_package()
                    name = ''
                    start = i
            elif state == STATE_OPERATOR:
                if c in SEPARATORS:
                    state = STATE_VERSION
                    op = content[start:i]
                    start = i + 1
                elif c not in OPERATORS:
                    state = STATE_VERSION
                    op = content[start:i]
                    start = i
            elif state == STATE_VERSION:
                if c in SEPARATORS:
                    if not version:
                        version = content[start:i]
                    if version:
                        process_package()
                        name = op = version = ''
                        state = STATE_NAME
                    start = i + 1
        if name:
            process_package()
        return packages

    def _lookup_requires(self, requires: T.List[RequiredVersion]) -> T.List['Package']:
        packages = []
        for req in requires:
            pkg = self.repo.lookup(req.name)
            if req.wanted and not version_compare(pkg.version, req.wanted):
                raise PkgConfigException(f'Version mismatch: wanted {req.wanted!r} but got {pkg.version!r}')
            packages.append(pkg)
        return packages

    def _get_transitive_requires(self) -> T.Set['Package']:
        packages = set()
        for pkg in itertools.chain(self.requires, self.requires_private):
            packages.add(pkg)
            packages.update(pkg._get_transitive_requires())
        return packages

    def _check_conflicts(self) -> None:
        packages = self._get_transitive_requires()
        for pkg in packages:
            for c in self.conflicts:
                if pkg.pkgname != c.name:
                    continue
                if not c.wanted or version_compare(pkg.version, c.wanted):
                    raise PkgConfigException(f'{self.pkgname} conflicts with {c.name}{c.wanted} but found version {pkg.version}')

    def _expand(self, content: str, variables: T.Dict[str, str]) -> str:
        dollar = False
        brackets = False
        start = 0
        line = ''
        for i, c in enumerate(content):
            if brackets:
                if c == '}':
                    brackets = False
                    varname = content[start:i]
                    try:
                        line += variables[varname]
                    except KeyError:
                        raise PkgConfigException(f'Variable {varname!r} not defined in {self.pkgname!r}')
                    start = i + 1
            elif dollar:
                if c == '{':
                    dollar = False
                    brackets = True
                    line += content[start:i-1]
                    start = i + 1
                elif c == '$':
                    line += content[start:i]
                    start = i + 1
                    dollar = False
            elif c == '$':
                dollar = True
        line += content[start:]
        return line

    def _readlines(self) -> T.Generator[str, None, None]:
        with open(self.filename, 'r', encoding='utf-8') as f:
            content = f.read()
        # Parse the file char by char. Avoid appending each char individually
        # into line string because that creates a new string each time, instead
        # keep track of the start of the chunk and append only once we found
        # a char that cannot be copied as-is.
        escaped = False
        comment = False
        start = 0
        line = ''
        for i, c in enumerate(itertools.chain(content, '\n')):
            # '\r' and '\r\n' are treated as if it was a single '\n' char
            if c == '\r':
                if content[i+1] == '\n':
                    continue
                c = '\n'
            if comment:
               # When inside a comment, ignore everything until end of line.
                if c == '\n':
                    comment = False
                    start = i + 1
            elif escaped:
                escaped = False
                if c == '\n':
                    # '\\n' - Skip both chars and continue current line.
                    start = i + 1
                elif c == '#':
                    # '\#' - Skip '\' and include '#'
                    start = i
                else:
                    # '\?' - Include both chars.
                    start = i - 1
            elif c == '\\':
                # Next char is escaped, copy everything we had so far.
                escaped = True
                line += content[start:i]
            elif c == '#':
                # '#' ends the current line. Next line will start after the
                # first '\n' we'll find.
                comment = True
                line += content[start:i]
                yield line
                line = ''
            elif c == '\n':
                # '\n' ends the current line. Next like starts at the next char.
                line += content[start:i]
                yield line
                line = ''
                start = i + 1

    def _get_args(self, args: T.List[str], system_args: T.List[str], allow_system_args: bool) -> T.List[str]:
        if allow_system_args:
            return args.copy()
        return [a for a in args if a not in system_args]

    def get_cflags(self, allow_system_cflags: bool = False) -> T.List[str]:
        cflags = self._get_args(self.cflags, self.repo.system_cflags, allow_system_cflags)
        for pkg in self.requires_private:
            cflags.extend(pkg.get_cflags(allow_system_cflags))
        for pkg in self.requires:
            cflags.extend(pkg.get_cflags(allow_system_cflags))
        return cflags

    def get_libs(self, static: bool, allow_system_libs: bool = False) -> T.List[str]:
        libs = self._get_args(self.libs, self.repo.system_libs, allow_system_libs)
        for pkg in self.requires:
            libs.extend(pkg.get_libs(static))
        if static:
            libs.extend(self._get_args(self.libs_private, self.repo.system_libs, allow_system_libs))
            for pkg in self.requires_private:
                libs.extend(pkg.get_libs(static))
        return libs

    def get_variable(self, varname: str, default: T.Optional[str] = None, overrides: T.Optional[T.Dict[str, str]] = None) -> str:
        if not overrides:
            return self.variables.get(varname, default)

        if varname in overrides:
            return overrides[varname]

        # Reevaluate all variables in order, with the overrides, until we find the one we want.
        variables = self.globals.copy()
        variables.update(overrides)
        for key, raw_value in self.raw_variables.items():
            if key in overrides:
                continue
            value = self._expand(raw_value, variables)
            if key == varname:
                return value
            variables[key] = value

        if default is not None:
            return default

        raise PkgConfigException(f'Unknown variable name: {varname!r}')

    def get_transitive_requires(self) -> T.List[str]:
        packages = self._get_transitive_requires()
        return [i.pkgname for i in packages]

class Repository:
    def __init__(self,
                 lookup_paths: T.List[Path],
                 system_include_paths: T.List[Path],
                 system_library_paths: T.List[Path],
                 sysroot_dir: T.Optional[Path],
                 sysroot_map: T.Dict[Path, Path],
                 disable_uninstalled: bool) -> None:
        self.lookup_paths = [p for p in lookup_paths if p.exists()]
        self.system_cflags = ['-I' + p.as_posix() for p in system_include_paths]
        self.system_libs = ['-L' + p.as_posix() for p in system_library_paths]
        self.sysroot_dir = sysroot_dir
        self.sysroot_map = sysroot_map
        self.disable_uninstalled = disable_uninstalled
        self.cache: T.Dict[str, Package] = {}
        self.recursion: T.List[str] = []

    def get_all(self) -> T.List[Package]:
        names = set()
        for d in self.lookup_paths:
            for f in d.glob('*.pc'):
                name = f.name.replace('-uninstalled.pc', '').replace('.pc', '')
                names.add(name)
        packages = []
        for name in names:
            try:
                packages.append(self.lookup(name))
            except PkgConfigException:
                pass
        return packages

    def lookup(self, name: str) -> Package:
        pkg = self.cache.get(name)
        if pkg:
            return pkg
        if name in self.recursion:
            stack = ' -> '.join(self.recursion + [name])
            raise PkgConfigException(f'Pkg-config recursion detected: {stack}')
        try:
            self.recursion.append(name)
            if not self.disable_uninstalled:
                pkg = self._lookup_internal(name, '-uninstalled.pc')
            if not pkg:
                pkg = self._lookup_internal(name, '.pc')
        finally:
            self.recursion.pop()
        if not pkg:
            raise PkgConfigException('Package not found: ' + name)
        self.cache[name] = pkg
        return pkg

    def _lookup_internal(self, name: str, suffix: str) -> T.Optional[Package]:
        fname = name + suffix
        for d in self.lookup_paths:
            filename = Path(d, fname)
            if filename.is_file():
                sysroot = self.sysroot_map.get(d, self.sysroot_dir)
                return Package(self, name, filename, sysroot)
        return None
