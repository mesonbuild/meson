# Copyright 2012-2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typing

from . import mesonlib

if typing.TYPE_CHECKING:
    from .coredata import OptionDictType
    from .environment import Environment


class StaticLinker:

    def __init__(self, exelist: typing.List[str]):
        self.exelist = exelist

    def can_linker_accept_rsp(self) -> bool:
        """
        Determines whether the linker can accept arguments using the @rsp syntax.
        """
        return mesonlib.is_windows()

    def get_base_link_args(self, options: 'OptionDictType') -> typing.List[str]:
        """Like compilers.get_base_link_args, but for the static linker."""
        return []

    def get_exelist(self) -> typing.List[str]:
        return self.exelist.copy()

    def get_std_link_args(self) -> typing.List[str]:
        return []

    def get_buildtype_linker_args(self, buildtype: str) -> typing.List[str]:
        return []

    def get_output_args(self, target: str) -> typing.List[str]:
        return[]

    def get_coverage_link_args(self) -> typing.List[str]:
        return []

    def build_rpath_args(self, build_dir: str, from_dir: str, rpath_paths: str,
                         build_rpath: str, install_rpath: str) -> typing.List[str]:
        return []

    def thread_link_flags(self, env: 'Environment') -> typing.List[str]:
        return []

    def openmp_flags(self) -> typing.List[str]:
        return []

    def get_option_link_args(self, options: 'OptionDictType') -> typing.List[str]:
        return []

    @classmethod
    def unix_args_to_native(cls, args: typing.List[str]) -> typing.List[str]:
        return args

    def get_link_debugfile_args(self, targetfile: str) -> typing.List[str]:
        # Static libraries do not have PDB files
        return []

    def get_always_args(self) -> typing.List[str]:
        return []

    def get_linker_always_args(self) -> typing.List[str]:
        return []


class VisualStudioLikeLinker:
    always_args = ['/NOLOGO']

    def __init__(self, machine: str):
        self.machine = machine

    def get_always_args(self) -> typing.List[str]:
        return self.always_args.copy()

    def get_linker_always_args(self) -> typing.List[str]:
        return self.always_args.copy()

    def get_output_args(self, target: str) -> typing.List[str]:
        args = []  # type: typing.List[str]
        if self.machine:
            args += ['/MACHINE:' + self.machine]
        args += ['/OUT:' + target]
        return args

    @classmethod
    def unix_args_to_native(cls, args: typing.List[str]) -> typing.List[str]:
        from .compilers import VisualStudioCCompiler
        return VisualStudioCCompiler.unix_args_to_native(args)


class VisualStudioLinker(VisualStudioLikeLinker, StaticLinker):

    """Microsoft's lib static linker."""

    def __init__(self, exelist: typing.List[str], machine: str):
        StaticLinker.__init__(self, exelist)
        VisualStudioLikeLinker.__init__(self, machine)


class IntelVisualStudioLinker(VisualStudioLikeLinker, StaticLinker):

    """Intel's xilib static linker."""

    def __init__(self, exelist: typing.List[str], machine: str):
        StaticLinker.__init__(self, exelist)
        VisualStudioLikeLinker.__init__(self, machine)


class ArLinker(StaticLinker):

    def __init__(self, exelist: typing.List[str]):
        super().__init__(exelist)
        self.id = 'ar'
        pc, stdo = mesonlib.Popen_safe(self.exelist + ['-h'])[0:2]
        # Enable deterministic builds if they are available.
        if '[D]' in stdo:
            self.std_args = ['csrD']
        else:
            self.std_args = ['csr']

    def get_std_link_args(self) -> typing.List[str]:
        return self.std_args

    def get_output_args(self, target: str) -> typing.List[str]:
        return [target]


class ArmarLinker(ArLinker):

    def __init__(self, exelist: typing.List[str]):
        StaticLinker.__init__(self, exelist)
        self.id = 'armar'
        self.std_args = ['-csr']

    def can_linker_accept_rsp(self) -> bool:
        # armar cann't accept arguments using the @rsp syntax
        return False


class DLinker(StaticLinker):
    def __init__(self, exelist: typing.List[str], arch: str):
        super().__init__(exelist)
        self.id = exelist[0]
        self.arch = arch

    def get_std_link_args(self) -> typing.List[str]:
        return ['-lib']

    def get_output_args(self, target: str) -> typing.List[str]:
        return ['-of=' + target]

    def get_linker_always_args(self) -> typing.List[str]:
        if mesonlib.is_windows():
            if self.arch == 'x86_64':
                return ['-m64']
            elif self.arch == 'x86_mscoff' and self.id == 'dmd':
                return ['-m32mscoff']
            return ['-m32']
        return []


class CcrxLinker(StaticLinker):

    def __init__(self, exelist: typing.List[str]):
        super().__init__(exelist)
        self.id = 'rlink'

    def can_linker_accept_rsp(self) -> bool:
        return False

    def get_output_args(self, target: str) -> typing.List[str]:
        return ['-output=%s' % target]

    def get_linker_always_args(self) -> typing.List[str]:
        return ['-nologo', '-form=library']
