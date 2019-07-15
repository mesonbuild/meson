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

import abc
import os
import shlex
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


class DynamicLinker(metaclass=abc.ABCMeta):

    """Base class for dynamic linkers."""

    _BUILDTYPE_ARGS = {
        'plain': [],
        'debug': [],
        'debugoptimized': [],
        'release': [],
        'minsize': [],
        'custom': [],
    }  # type: typing.Dict[str, typing.List[str]]

    def __init__(self, exelist: typing.List[str], for_machine: mesonlib.MachineChoice,
                 id_: str, *, version: str = 'unknown version'):
        self.exelist = exelist
        self.for_machine = for_machine
        self.version = version
        self.id = id_

    def __repr__(self) -> str:
        return '<{}: v{} `{}`>'.format(type(self).__name__, self.version, ' '.join(self.exelist))

    def get_id(self) -> str:
        return self.id

    def get_version_string(self) -> str:
        return '({} {})'.format(self.id, self.version)

    def get_exelist(self) -> typing.List[str]:
        return self.exelist.copy()

    def get_accepts_rsp(self) -> bool:
        # TODO: is it really a matter of is_windows or is it for_windows?
        return mesonlib.is_windows()

    def get_always_args(self) -> typing.List[str]:
        return []

    def get_lib_prefix(self) -> str:
        return ''

    # XXX: is use_ldflags a compiler or a linker attribute?

    def get_args_from_envvars(self) -> typing.List[str]:
        flags = os.environ.get('LDFLAGS')
        if not flags:
            return []
        return shlex.split(flags)

    def get_option_args(self, options: 'OptionDictType') -> typing.List[str]:
        return []

    def has_multi_arguments(self, args: typing.List[str], env: 'Environment') -> typing.Tuple[bool, bool]:
        m = 'Language {} does not support has_multi_link_arguments.'
        raise mesonlib.EnvironmentException(m.format(self.id))

    def get_debugfile_args(self, targetfile: str) -> typing.List[str]:
        """Some compilers (MSVC) write debug into a separate file.

        This method takes the target object path and returns a list of
        commands to append to the linker invocation to control where that
        file is written.
        """
        return []

    def get_std_shared_lib_args(self) -> typing.List[str]:
        return []

    def get_std_shared_module_args(self, options: 'OptionDictType') -> typing.List[str]:
        return self.get_std_shared_lib_args()

    def get_pie_args(self) -> typing.List[str]:
        # TODO: this really needs to take a boolean and return the args to
        # disable pie, otherwise it only acts to enable pie if pie *isn't* the
        # default.
        m = 'Linker {} does not support position-independent executable'
        raise mesonlib.EnvironmentException(m.format(self.id))

    def get_lto_args(self) -> typing.List[str]:
        return []

    def sanitizer_args(self, value: str) -> typing.List[str]:
        return []

    def get_buildtype_args(self, buildtype: str) -> typing.List[str]:
        # We can override these in children by just overriding the
        # _BUILDTYPE_ARGS value.
        return self._BUILDTYPE_ARGS[buildtype]

    def get_asneeded_args(self) -> typing.List[str]:
        return []

    def get_link_whole_for(self, args: typing.List[str]) -> typing.List[str]:
        raise mesonlib.EnvironmentException(
            'Linker {} does not support link_whole'.format(self.id))

    def get_allow_undefined_args(self) -> typing.List[str]:
        raise mesonlib.EnvironmentException(
            'Linker {} does not support allow undefined'.format(self.id))

    def invoked_by_compiler(self) -> bool:
        """True if meson uses the compiler to invoke the linker."""
        return True

    @abc.abstractmethod
    def get_output_args(self, outname: str) -> typing.List[str]:
        pass

    def get_coverage_args(self) -> typing.List[str]:
        m = "Linker {} doesn't implement coverage data generation.".format(self.id)
        raise mesonlib.EnvironmentException(m)

    @abc.abstractmethod
    def get_search_args(self, dirname: str) -> typing.List[str]:
        pass

    def export_dynamic_args(self, env: 'Environment') -> typing.List[str]:
        return []

    def import_library_args(self, implibname: str) -> typing.List[str]:
        """The name of the outputted import library.

        This implementation is used only on Windows by compilers that use GNU ld
        """
        return []

    def thread_flags(self, env: 'Environment') -> typing.List[str]:
        return []

    def no_undefined_args(self) -> typing.List[str]:
        """Arguments to error if there are any undefined symbols at link time.

        This is the inverse of get_allow_undefined_args().

        TODO: A future cleanup might merge this and
              get_allow_undefined_args() into a single method taking a
              boolean
        """
        return []

    def fatal_warnings(self) -> typing.List[str]:
        """Arguments to make all warnings errors."""
        return []

    def bitcode_args(self) -> typing.List[str]:
        raise mesonlib.MesonException('This linker does not support bitcode bundles')

    def get_debug_crt_args(self) -> typing.List[str]:
        return []

    def build_rpath_args(self, env: 'Environment', build_dir: str, from_dir: str,
                         rpath_paths: str, build_rpath: str,
                         install_rpath: str) -> typing.List[str]:
        return []


class PosixDynamicLinkerMixin:

    """Mixin class for POSIX-ish linkers.

    This is obviously a pretty small subset of the linker interface, but
    enough dynamic linkers that meson supports are POSIX-like but not
    GNU-like that it makes sense to split this out.
    """

    def get_output_args(self, outname: str) -> typing.List[str]:
        return ['-o', outname]

    def get_std_shared_lib_args(self) -> typing.List[str]:
        return ['-shared']

    def get_search_args(self, dirname: str) -> typing.List[str]:
        return ['-L', dirname]
