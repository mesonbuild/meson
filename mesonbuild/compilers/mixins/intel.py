# Copyright 2019 The meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Abstractions for the Intel Compiler families.

Intel provides both a posix/gcc-like compiler (ICC) and an msvc-like compiler
(ICL).
"""

import os
import typing

from ... import mesonlib
from ..compilers import CompilerType
from .gnu import GnuLikeCompiler
from .visualstudio import VisualStudioLikeCompiler

if typing.TYPE_CHECKING:
    import subprocess  # noqa: F401

# XXX: avoid circular dependencies
# TODO: this belongs in a posix compiler class
clike_optimization_args = {
    '0': [],
    'g': [],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': ['-Os'],
}  # type: typing.Dict[str, typing.List[str]]


# Tested on linux for ICC 14.0.3, 15.0.6, 16.0.4, 17.0.1, 19.0.0
class IntelGnuLikeCompiler(GnuLikeCompiler):

    def __init__(self, compiler_type: 'CompilerType'):
        super().__init__(compiler_type)
        # As of 19.0.0 ICC doesn't have sanitizer, color, or lto support.
        #
        # It does have IPO, which serves much the same purpose as LOT, but
        # there is an unfortunate rule for using IPO (you can't control the
        # name of the output file) which break assumptions meson makes
        self.base_options = ['b_pch', 'b_lundef', 'b_asneeded', 'b_pgo',
                             'b_coverage', 'b_ndebug', 'b_staticpic', 'b_pie']
        self.id = 'intel'
        self.lang_header = 'none'

    def get_optimization_args(self, optimization_level: str) -> typing.List[str]:
        return clike_optimization_args[optimization_level]

    def get_pch_suffix(self) -> str:
        return 'pchi'

    def get_pch_use_args(self, pch_dir: str, header: str) -> typing.List[str]:
        return ['-pch', '-pch_dir', os.path.join(pch_dir), '-x',
                self.lang_header, '-include', header, '-x', 'none']

    def get_pch_name(self, header_name: str) -> str:
        return os.path.basename(header_name) + '.' + self.get_pch_suffix()

    def openmp_flags(self) -> typing.List[str]:
        if mesonlib.version_compare(self.version, '>=15.0.0'):
            return ['-qopenmp']
        else:
            return ['-openmp']

    def compiles(self, *args, **kwargs) -> typing.Tuple[bool, bool]:
        # This covers a case that .get('foo', []) doesn't, that extra_args is
        # defined and is None
        extra_args = kwargs.get('extra_args') or []
        kwargs['extra_args'] = [
            extra_args,
            '-diag-error', '10006',  # ignoring unknown option
            '-diag-error', '10148',  # Option not supported
            '-diag-error', '10155',  # ignoring argument required
            '-diag-error', '10156',  # ignoring not argument allowed
            '-diag-error', '10157',  # Ignoring argument of the wrong type
            '-diag-error', '10158',  # Argument must be separate. Can be hit by trying an option like -foo-bar=foo when -foo=bar is a valid option but -foo-bar isn't
            '-diag-error', '1292',   # unknown __attribute__
        ]
        return super().compiles(*args, **kwargs)

    def get_profile_generate_args(self) -> typing.List[str]:
        return ['-prof-gen=threadsafe']

    def get_profile_use_args(self) -> typing.List[str]:
        return ['-prof-use']


class IntelVisualStudioLikeCompiler(VisualStudioLikeCompiler):

    """Abstractions for ICL, the Intel compiler on Windows."""

    def __init__(self, target: str):
        super().__init__(target)
        self.compiler_type = CompilerType.ICC_WIN
        self.id = 'intel-cl'

    def compile(self, code, *, extra_args: typing.Optional[typing.List[str]] = None, **kwargs) -> typing.Iterator['subprocess.Popen']:
        # This covers a case that .get('foo', []) doesn't, that extra_args is
        if kwargs.get('mode', 'compile') != 'link':
            extra_args = extra_args.copy() if extra_args is not None else []
            extra_args.extend([
                '/Qdiag-error:10006',  # ignoring unknown option
                '/Qdiag-error:10148',  # Option not supported
                '/Qdiag-error:10155',  # ignoring argument required
                '/Qdiag-error:10156',  # ignoring not argument allowed
                '/Qdiag-error:10157',  # Ignoring argument of the wrong type
                '/Qdiag-error:10158',  # Argument must be separate. Can be hit by trying an option like -foo-bar=foo when -foo=bar is a valid option but -foo-bar isn't
            ])
        return super().compile(code, extra_args, **kwargs)

    def get_toolset_version(self) -> typing.Optional[str]:
        # Avoid circular dependencies....
        from ...environment import search_version

        # ICL provides a cl.exe that returns the version of MSVC it tries to
        # emulate, so we'll get the version from that and pass it to the same
        # function the real MSVC uses to calculate the toolset version.
        _, _, err = mesonlib.Popen_safe(['cl.exe'])
        v1, v2, *_ = search_version(err).split('.')
        version = int(v1 + v2)
        return self._calculate_toolset_version(version)

    def openmp_flags(self) -> typing.List[str]:
        return ['/Qopenmp']
