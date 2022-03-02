# Copyright 2012-2021 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from ..mesonlib import (
    EnvironmentException, OptionKey,
    Popen_safe, search_version
)
from .linkers import (
    AppleDynamicLinker,
    GnuGoldDynamicLinker,
    GnuBFDDynamicLinker,
    LLVMDynamicLinker,
    QualcommLLVMDynamicLinker,
    MSVCDynamicLinker,
    ClangClDynamicLinker,
    SolarisDynamicLinker,
    AIXDynamicLinker,
    OptlinkDynamicLinker,
)

import re
import shlex
import typing as T

if T.TYPE_CHECKING:
    from .linkers import DynamicLinker, GnuDynamicLinker
    from ..environment import Environment
    from ..compilers import Compiler
    from ..mesonlib import MachineChoice

defaults: T.Dict[str, T.List[str]] = {}
defaults['static_linker'] = ['ar', 'gar']
defaults['vs_static_linker'] = ['lib']
defaults['clang_cl_static_linker'] = ['llvm-lib']
defaults['cuda_static_linker'] = ['nvlink']
defaults['gcc_static_linker'] = ['gcc-ar']
defaults['clang_static_linker'] = ['llvm-ar']

def __failed_to_detect_linker(compiler: T.List[str], args: T.List[str], stdout: str, stderr: str) -> 'T.NoReturn':
    msg = 'Unable to detect linker for compiler "{} {}"\nstdout: {}\nstderr: {}'.format(
        ' '.join(compiler), ' '.join(args), stdout, stderr)
    raise EnvironmentException(msg)


def guess_win_linker(env: 'Environment', compiler: T.List[str], comp_class: T.Type['Compiler'],
                     for_machine: MachineChoice, *,
                     use_linker_prefix: bool = True, invoked_directly: bool = True,
                     extra_args: T.Optional[T.List[str]] = None) -> 'DynamicLinker':
    env.coredata.add_lang_args(comp_class.language, comp_class, for_machine, env)

    # Explicitly pass logo here so that we can get the version of link.exe
    if not use_linker_prefix or comp_class.LINKER_PREFIX is None:
        check_args = ['/logo', '--version']
    elif isinstance(comp_class.LINKER_PREFIX, str):
        check_args = [comp_class.LINKER_PREFIX + '/logo', comp_class.LINKER_PREFIX + '--version']
    elif isinstance(comp_class.LINKER_PREFIX, list):
        check_args = comp_class.LINKER_PREFIX + ['/logo'] + comp_class.LINKER_PREFIX + ['--version']

    check_args += env.coredata.options[OptionKey('args', lang=comp_class.language, machine=for_machine)].value

    override = []  # type: T.List[str]
    value = env.lookup_binary_entry(for_machine, comp_class.language + '_ld')
    if value is not None:
        override = comp_class.use_linker_args(value[0])
        check_args += override

    if extra_args is not None:
        check_args.extend(extra_args)

    p, o, _ = Popen_safe(compiler + check_args)
    if 'LLD' in o.split('\n')[0]:
        if '(compatible with GNU linkers)' in o:
            return LLVMDynamicLinker(
                compiler, for_machine, comp_class.LINKER_PREFIX,
                override, version=search_version(o))
        elif not invoked_directly:
            return ClangClDynamicLinker(
                for_machine, override, exelist=compiler, prefix=comp_class.LINKER_PREFIX,
                version=search_version(o), direct=False, machine=None)

    if value is not None and invoked_directly:
        compiler = value
        # We've already hanedled the non-direct case above

    p, o, e = Popen_safe(compiler + check_args)
    if 'LLD' in o.split('\n')[0]:
        return ClangClDynamicLinker(
            for_machine, [],
            prefix=comp_class.LINKER_PREFIX if use_linker_prefix else [],
            exelist=compiler, version=search_version(o), direct=invoked_directly)
    elif 'OPTLINK' in o:
        # Opltink's stdout *may* beging with a \r character.
        return OptlinkDynamicLinker(compiler, for_machine, version=search_version(o))
    elif o.startswith('Microsoft') or e.startswith('Microsoft'):
        out = o or e
        match = re.search(r'.*(X86|X64|ARM|ARM64).*', out)
        if match:
            target = str(match.group(1))
        else:
            target = 'x86'

        return MSVCDynamicLinker(
            for_machine, [], machine=target, exelist=compiler,
            prefix=comp_class.LINKER_PREFIX if use_linker_prefix else [],
            version=search_version(out), direct=invoked_directly)
    elif 'GNU coreutils' in o:
        import shutil
        fullpath = shutil.which(compiler[0])
        raise EnvironmentException(
            f"Found GNU link.exe instead of MSVC link.exe in {fullpath}.\n"
            "This link.exe is not a linker.\n"
            "You may need to reorder entries to your %PATH% variable to resolve this.")
    __failed_to_detect_linker(compiler, check_args, o, e)

def guess_nix_linker(env: 'Environment', compiler: T.List[str], comp_class: T.Type['Compiler'],
                     for_machine: MachineChoice, *,
                     extra_args: T.Optional[T.List[str]] = None) -> 'DynamicLinker':
    """Helper for guessing what linker to use on Unix-Like OSes.

    :compiler: Invocation to use to get linker
    :comp_class: The Compiler Type (uninstantiated)
    :for_machine: which machine this linker targets
    :extra_args: Any additional arguments required (such as a source file)
    """
    env.coredata.add_lang_args(comp_class.language, comp_class, for_machine, env)
    extra_args = extra_args or []
    extra_args += env.coredata.options[OptionKey('args', lang=comp_class.language, machine=for_machine)].value

    if isinstance(comp_class.LINKER_PREFIX, str):
        check_args = [comp_class.LINKER_PREFIX + '--version'] + extra_args
    else:
        check_args = comp_class.LINKER_PREFIX + ['--version'] + extra_args

    override = []  # type: T.List[str]
    value = env.lookup_binary_entry(for_machine, comp_class.language + '_ld')
    if value is not None:
        override = comp_class.use_linker_args(value[0])
        check_args += override

    _, o, e = Popen_safe(compiler + check_args)
    v = search_version(o + e)
    linker: DynamicLinker
    if 'LLD' in o.split('\n')[0]:
        linker = LLVMDynamicLinker(
            compiler, for_machine, comp_class.LINKER_PREFIX, override, version=v)
    elif 'Snapdragon' in e and 'LLVM' in e:
        linker = QualcommLLVMDynamicLinker(
            compiler, for_machine, comp_class.LINKER_PREFIX, override, version=v)
    elif e.startswith('lld-link: '):
        # The LLD MinGW frontend didn't respond to --version before version 9.0.0,
        # and produced an error message about failing to link (when no object
        # files were specified), instead of printing the version number.
        # Let's try to extract the linker invocation command to grab the version.

        _, o, e = Popen_safe(compiler + check_args + ['-v'])

        try:
            linker_cmd = re.match(r'.*\n(.*?)\nlld-link: ', e, re.DOTALL).group(1)
            linker_cmd = shlex.split(linker_cmd)[0]
        except (AttributeError, IndexError, ValueError):
            pass
        else:
            _, o, e = Popen_safe([linker_cmd, '--version'])
            v = search_version(o)

        linker = LLVMDynamicLinker(compiler, for_machine, comp_class.LINKER_PREFIX, override, version=v)
    # first is for apple clang, second is for real gcc, the third is icc
    elif e.endswith('(use -v to see invocation)\n') or 'macosx_version' in e or 'ld: unknown option:' in e:
        if isinstance(comp_class.LINKER_PREFIX, str):
            _, _, e = Popen_safe(compiler + [comp_class.LINKER_PREFIX + '-v'] + extra_args)
        else:
            _, _, e = Popen_safe(compiler + comp_class.LINKER_PREFIX + ['-v'] + extra_args)
        for line in e.split('\n'):
            if 'PROJECT:ld' in line:
                v = line.split('-')[1]
                break
        else:
            v = 'unknown version'
        linker = AppleDynamicLinker(compiler, for_machine, comp_class.LINKER_PREFIX, override, version=v)
    elif 'GNU' in o or 'GNU' in e:
        cls: T.Type[GnuDynamicLinker]
        if 'gold' in o or 'gold' in e:
            cls = GnuGoldDynamicLinker
        else:
            cls = GnuBFDDynamicLinker
        linker = cls(compiler, for_machine, comp_class.LINKER_PREFIX, override, version=v)
    elif 'Solaris' in e or 'Solaris' in o:
        for line in (o+e).split('\n'):
            if 'ld: Software Generation Utilities' in line:
                v = line.split(':')[2].lstrip()
                break
        else:
            v = 'unknown version'
        linker = SolarisDynamicLinker(
            compiler, for_machine, comp_class.LINKER_PREFIX, override,
            version=v)
    elif 'ld: 0706-012 The -- flag is not recognized' in e:
        if isinstance(comp_class.LINKER_PREFIX, str):
            _, _, e = Popen_safe(compiler + [comp_class.LINKER_PREFIX + '-V'] + extra_args)
        else:
            _, _, e = Popen_safe(compiler + comp_class.LINKER_PREFIX + ['-V'] + extra_args)
        linker = AIXDynamicLinker(
            compiler, for_machine, comp_class.LINKER_PREFIX, override,
            version=search_version(e))
    else:
        __failed_to_detect_linker(compiler, check_args, o, e)
    return linker
