# SPDX-License-Identifier: Apache-2.0
# Copyright 2017-2025 The Meson development team

from __future__ import annotations

import dataclasses
import re
import typing as T

from .. import mlog
from ..mesonlib import listify, version_compare
from ..compilers.cuda import CudaCompiler
from ..interpreter.type_checking import NoneType

from . import NewExtensionModule, ModuleInfo

from ..utils.universal import Version
from ..interpreterbase import (
    ContainerTypeInfo, InvalidArguments, KwargInfo, noKwargs, typed_kwargs, typed_pos_args,
)

if T.TYPE_CHECKING:
    from typing_extensions import TypedDict

    from . import ModuleState
    from ..interpreter import Interpreter
    from ..interpreterbase import TYPE_var

    class ArchFlagsKwargs(TypedDict):
        detected: T.Optional[T.List[str]]

    AutoArch = T.Union[str, T.List[str]]


DETECTED_KW: KwargInfo[T.Union[None, T.List[str]]] = KwargInfo('detected', (ContainerTypeInfo(list, str), NoneType), listify=True)


@dataclasses.dataclass(slots=True)
class _CudaVersion:

    meson: str
    windows: str
    linux: str

    def compare(self, version: str, machine: str) -> T.Optional[str]:
        if version_compare(version, f'>={self.meson}'):
            return self.windows if machine == 'windows' else self.linux
        return None


# Copied from: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html#id7
_DRIVER_TABLE_VERSION: T.List[_CudaVersion] = [
    _CudaVersion('13.3.1', 'unknown', '610.43.02'),
    _CudaVersion('13.3.0', 'unknown', '610.43.02'),
    _CudaVersion('13.2.1', 'unknown', '595.58.03'),
    _CudaVersion('13.2.0', 'unknown', '595.45.04'),
    _CudaVersion('13.1.1', 'unknown', '590.48.01'),
    _CudaVersion('13.1.0', 'unknown', '590.44.01'),
    _CudaVersion('13.0.2', 'unknown', '580.95.05'),
    _CudaVersion('13.0.1', 'unknown', '580.82.07'),
    _CudaVersion('13.0.0', 'unknown', '580.65.06'),
    _CudaVersion('12.9.1', '576.57', '575.57.08'),
    _CudaVersion('12.9.0', '576.02', '575.51.03'),
    _CudaVersion('12.8.1', '572.61', '570.124.06'),
    _CudaVersion('12.8.0', '570.65', '570.26'),
    _CudaVersion('12.6.3', '561.17', '560.35.05'),
    _CudaVersion('12.6.2', '560.94', '560.35.03'),
    _CudaVersion('12.6.1', '560.94', '560.35.03'),
    _CudaVersion('12.6.0', '560.76', '560.28.03'),
    _CudaVersion('12.5.1', '555.85', '555.42.06'),
    _CudaVersion('12.5.0', '555.85', '555.42.02'),
    _CudaVersion('12.4.1', '551.78', '550.54.15'),
    _CudaVersion('12.4.0', '551.61', '550.54.14'),
    _CudaVersion('12.3.1', '546.12', '545.23.08'),
    _CudaVersion('12.3.0', '545.84', '545.23.06'),
    _CudaVersion('12.2.2', '537.13', '535.104.05'),
    _CudaVersion('12.2.1', '536.67', '535.86.09'),
    _CudaVersion('12.2.0', '536.25', '535.54.03'),
    _CudaVersion('12.1.1', '531.14', '530.30.02'),
    _CudaVersion('12.1.0', '531.14', '530.30.02'),
    _CudaVersion('12.0.1', '528.33', '525.85.11'),
    _CudaVersion('12.0.0', '527.41', '525.60.13'),
    _CudaVersion('11.8.0', '522.06', '520.61.05'),
    _CudaVersion('11.7.1', '516.31', '515.48.07'),
    _CudaVersion('11.7.0', '516.01', '515.43.04'),
    _CudaVersion('11.6.1', '511.65', '510.47.03'),  # 11.6.2 is identical
    _CudaVersion('11.6.0', '511.23', '510.39.01'),
    _CudaVersion('11.5.1', '496.13', '495.29.05'),  # 11.5.2 is identical
    _CudaVersion('11.5.0', '496.04', '495.29.05'),
    _CudaVersion('11.4.3', '472.50', '470.82.01'),  # 11.4.4 is identical
    _CudaVersion('11.4.1', '471.41', '470.57.02'),  # 11.4.2 is identical
    _CudaVersion('11.4.0', '471.11', '470.42.01'),
    _CudaVersion('11.3.0', '465.89', '465.19.01'),  # 11.3.1 is identical
    _CudaVersion('11.2.2', '461.33', '460.32.03'),
    _CudaVersion('11.2.1', '461.09', '460.32.03'),
    _CudaVersion('11.2.0', '460.82', '460.27.03'),
    _CudaVersion('11.1.1', '456.81', '455.32'),
    _CudaVersion('11.1.0', '456.38', '455.23'),
    _CudaVersion('11.0.3', '451.82', '450.51.06'),  # 11.0.3.1 is identical
    _CudaVersion('11.0.2', '451.48', '450.51.05'),
    _CudaVersion('11.0.1', '451.22', '450.36.06'),
    _CudaVersion('10.2.89', '441.22', '440.33'),
    _CudaVersion('10.1.105', '418.96', '418.39'),
    _CudaVersion('10.0.130', '411.31', '410.48'),
    _CudaVersion('9.2.148', '398.26', '396.37'),
    _CudaVersion('9.2.88', '397.44', '396.26'),
    _CudaVersion('9.1.85', '391.29', '390.46'),
    _CudaVersion('9.0.76', '385.54', '384.81'),
    _CudaVersion('8.0.61', '376.51', '375.26'),
    _CudaVersion('8.0.44', '369.30', '367.48'),
    _CudaVersion('7.5.16', '353.66', '352.31'),
    _CudaVersion('7.0.28', '347.62', '346.46'),
]


@dataclasses.dataclass(slots=True)
class _IsaDef:

    # half-open range, i.e., support for '2.0'/sm_20 is included in CUDA 3.0 <= cuda_version < 9.0
    min_cuda_ver: str  # included
    max_cuda_ver: T.Optional[str]  # excluded; None = still supported
    common: bool       # considered "common" for when user passes 'Common' arg
    virt: T.Optional[str] = None   # virtual arch, if it differs from the code arch (sm_21 has no compute_21)

    def cuda_too_old(self, cuda_version: str) -> bool:
        return version_compare(cuda_version, '<' + self.min_cuda_ver)

    def arch_too_old(self, cuda_version: str) -> bool:
        return self.max_cuda_ver is not None and version_compare(cuda_version, '>=' + self.max_cuda_ver)

    def supports(self, cuda_version: str) -> bool:
        return not self.cuda_too_old(cuda_version) and not self.arch_too_old(cuda_version)

# Replicates https://en.wikipedia.org/wiki/CUDA#GPUs_supported
# a max_cuda_ver of None denotes an arch that is still fully supported as of 2026-07-13
_MICROISA_RANGES_DEF: T.Mapping[str, _IsaDef] = {
    ### Fermi
     '2.0':  _IsaDef( '3.0',  '9.0', False), # GF100/GF110
     '2.1':  _IsaDef( '3.2',  '9.0', False, virt='2.0'), # GF104/GF106/GF108/GF114/GF116/GF117/GF119
    ### Kepler
     '3.0':  _IsaDef( '5.0', '11.0', True),  # GK104/GK106/GK107
     '3.2':  _IsaDef( '6.0', '11.0', False), # GK20A (Tegra/Jetson K1)
     '3.5':  _IsaDef( '5.0', '12.0', True),  # GK110/GK208
     '3.7':  _IsaDef( '6.5', '12.0', False), # GK210 (Tesla K80)
    ### Maxwell
     '5.0':  _IsaDef( '6.5', '13.0', True),  # GM107/GM108
     '5.2':  _IsaDef( '6.5', '13.0', True),  # GM200/GM204/GM206
     '5.3':  _IsaDef( '6.5', '13.0', False), # GM20B (Tegra/Jetson X1)
    ### Pascal
     '6.0':  _IsaDef( '8.0', '13.0', True),  # GP100
     '6.1':  _IsaDef( '8.0', '13.0', True),  # GP102/GP104/GP106/GP107/GP108
     '6.2':  _IsaDef( '8.0', '13.0', False), # GP10B (Tegra/Jetson X2)
    ### Volta
     '7.0':  _IsaDef( '9.0', '13.0', True),  # GV100
     '7.2':  _IsaDef('10.0', '13.0', False), # GV10B/GV11B (Tegra/Jetson Xavier)
    ### Turing
     '7.5':  _IsaDef('10.0', None,   True),  # TU102/TU104/TU106/TU116/TU117
    ### Ampere
     '8.0':  _IsaDef('11.0', None,   True),  # GA100
     '8.6':  _IsaDef('11.1', None,   True),  # GA102/GA103/GA104/GA106/GA107
     '8.7':  _IsaDef('11.5', None,   False), # GA10B (Jetson Orin)
     '8.8':  _IsaDef('13.0', None,   False), # undocumented Ampere variant
    ### Lovelace
     '8.9':  _IsaDef('11.8', None,   True),  # AD102/AD103/AD104/AD106/AD107
    ### Hopper
     '9.0a': _IsaDef('12.0', None,   False), # GH100 (no minor backcompat)
     '9.0':  _IsaDef('11.8', None,   True),  # GH100
    ### Blackwell
    # CUDA 12.9 added 'X.Yf' specifiers
    # https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/
    '10.0a': _IsaDef('12.8', None,   False), # GB100 (no minor backcompat)
    '10.0f': _IsaDef('12.9', None,   False), # GB100
    '10.0':  _IsaDef('12.8', None,   True),  # GB100
    '10.1a': _IsaDef('12.8', '13.0', False), # GB10B (Jetson Thor) (changed to 11.0 in CUDA 13) (no minor backcompat)
    '10.1f': _IsaDef('12.9', '13.0', False), # GB10B (Jetson Thor) (changed to 11.0 in CUDA 13)
    '10.1':  _IsaDef('12.8', '13.0', False), # GB10B (Jetson Thor) (changed to 11.0 in CUDA 13)
    '10.3a': _IsaDef('12.9', None,   False), # GB110 (no minor backcompat)
    '10.3f': _IsaDef('12.9', None,   False), # GB110
    '10.3':  _IsaDef('12.9', None,   True),  # GB110
    '11.0a': _IsaDef('13.0', None,   False), # GB10B (Jetson Thor) (no minor backcompat)
    '11.0f': _IsaDef('13.0', None,   False), # GB10B (Jetson Thor)
    '11.0':  _IsaDef('13.0', None,   False), # GB10B (Jetson Thor)
    '12.0a': _IsaDef('12.9', None,   False), # GB100/GB202/GB203/GB205/GB206/GB207 (no minor backcompat)
    '12.0f': _IsaDef('12.9', None,   False), # GB100/GB202/GB203/GB205/GB206/GB207
    '12.0':  _IsaDef('12.8', None,   True),  # GB100/GB202/GB203/GB205/GB206/GB207
    '12.1a': _IsaDef('12.9', None,   False), # GB20B (no minor backcompat)
    '12.1f': _IsaDef('12.9', None,   False), # GB20B
    '12.1':  _IsaDef('12.9', None,   True),  # GB20B
}

_FAMILY_TO_MICROISAS: T.Mapping[str, T.FrozenSet[str]] = {
    'Fermi':         frozenset(['2.0', '2.1']),
    'Kepler':        frozenset(['3.0', '3.5']),
    'Kepler+Tegra':  frozenset(['3.2']),
    'Kepler+Tesla':  frozenset(['3.7']),
    'Maxwell':       frozenset(['5.0', '5.2']),
    'Maxwell+Tegra': frozenset(['5.3']),
    'Pascal':        frozenset(['6.0', '6.1']),
    'Pascal+Tegra':  frozenset(['6.2']),
    'Volta':         frozenset(['7.0']),
    'Xavier':        frozenset(['7.2']),
    'Turing':        frozenset(['7.5']),
    'Ampere':        frozenset(['8.0', '8.6']),
    'Orin':          frozenset(['8.7']),
    'Lovelace':      frozenset(['8.9']),
    'Hopper':        frozenset(['9.0']),
    'Hopper(A)':     frozenset(['9.0a']),
    'Thor':          frozenset(['10.1', '11.0']),
    'Thor(A)':       frozenset(['10.1a', '11.0a']),
    'Blackwell':     frozenset(['10.0', '10.3', '12.0', '12.1']),
    'Blackwell(A)':  frozenset(['10.0a', '10.3a', '12.0a', '12.1a']),
}

# reverse lookup for family-specific ('f') pairing checks; '(A)' pseudo-families excluded
_ISA_TO_FAMILY: T.Mapping[str, str] = {isa: family
                                       for family, isas in _FAMILY_TO_MICROISAS.items() if not family.endswith('(A)')
                                       for isa in isas}

# a single micro-ISA, e.g. '8.6', '9.0a' or '10.0f'
_MICROISA_RE = re.compile(r'[0-9]+\.[0-9][af]?')
# an output micro-ISA with an optional virtual micro-ISA, e.g. '12.0a' or '8.6(8.0)'
_ARCH_SPEC_RE = re.compile(rf'({_MICROISA_RE.pattern})(?:\(({_MICROISA_RE.pattern})\))?')


class CudaModule(NewExtensionModule):

    INFO = ModuleInfo('CUDA', '0.50.0', unstable=True)

    def __init__(self, interp: Interpreter):
        super().__init__()
        self.methods.update({
            "min_driver_version": self.min_driver_version,
            "nvcc_arch_flags":    self.nvcc_arch_flags,
            "nvcc_arch_readable": self.nvcc_arch_readable,
        })

    @noKwargs
    def min_driver_version(self, state: 'ModuleState',
                           args: T.List[TYPE_var],
                           kwargs: T.Dict[str, T.Any]) -> str:
        argerror = InvalidArguments('min_driver_version must have exactly one positional argument: ' +
                                    'a CUDA Toolkit version string. Beware that, since CUDA 11.0, ' +
                                    'the CUDA Toolkit\'s components (including NVCC) are versioned ' +
                                    'independently from each other (and the CUDA Toolkit as a whole).')
        if len(args) != 1 or not isinstance(args[0], str):
            raise argerror

        cuda_version = args[0]

        for d in _DRIVER_TABLE_VERSION:
            driver_version = d.compare(cuda_version, state.environment.machines.host.system)
            if driver_version is not None:
                return driver_version
        return 'unknown'

    @typed_pos_args('cuda.nvcc_arch_flags', (str, CudaCompiler), varargs=str)
    @typed_kwargs('cuda.nvcc_arch_flags', DETECTED_KW)
    def nvcc_arch_flags(self, state: 'ModuleState',
                        args: T.Tuple[T.Union[CudaCompiler, str], T.List[str]],
                        kwargs: ArchFlagsKwargs) -> T.List[str]:
        nvcc_arch_args = self._validate_nvcc_arch_args(args, kwargs)
        ret = self._nvcc_arch_flags(*nvcc_arch_args)[0]
        return ret

    @typed_pos_args('cuda.nvcc_arch_readable', (str, CudaCompiler), varargs=str)
    @typed_kwargs('cuda.nvcc_arch_readable', DETECTED_KW)
    def nvcc_arch_readable(self, state: 'ModuleState',
                           args: T.Tuple[T.Union[CudaCompiler, str], T.List[str]],
                           kwargs: ArchFlagsKwargs) -> T.List[str]:
        nvcc_arch_args = self._validate_nvcc_arch_args(args, kwargs)
        ret = self._nvcc_arch_flags(*nvcc_arch_args)[1]
        return ret

    @staticmethod
    def _break_arch_string(s: str) -> T.List[str]:
        s = re.sub('[ \t\r\n,;]+', ';', s)
        return s.strip(';').split(';')

    @staticmethod
    def _detected_cc_from_compiler(c: T.Union[str, CudaCompiler]) -> T.List[str]:
        if isinstance(c, CudaCompiler):
            return [c.detected_cc]
        return []

    def _validate_nvcc_arch_args(self, args: T.Tuple[T.Union[str, CudaCompiler], T.List[str]],
                                 kwargs: ArchFlagsKwargs) -> T.Tuple[str, AutoArch, T.List[str]]:

        compiler = args[0]
        if isinstance(compiler, CudaCompiler):
            cuda_version = compiler.version
        else:
            cuda_version = compiler

        arch_list: AutoArch = args[1]
        arch_list = listify([self._break_arch_string(a) for a in arch_list])
        if len(arch_list) > 1 and not set(arch_list).isdisjoint({'All', 'Common', 'Auto'}):
            raise InvalidArguments('''The special architectures 'All', 'Common' and 'Auto' must appear alone, as a positional argument!''')
        arch_list = arch_list[0] if len(arch_list) == 1 else arch_list

        detected = kwargs['detected'] if kwargs['detected'] is not None else self._detected_cc_from_compiler(compiler)
        detected = [x for a in detected for x in self._break_arch_string(a)]
        if not set(detected).isdisjoint({'All', 'Common', 'Auto'}):
            raise InvalidArguments('''The special architectures 'All', 'Common' and 'Auto' must appear alone, as a positional argument!''')

        return cuda_version, arch_list, detected

    @staticmethod
    def _nvcc_arch_flags(cuda_version: str, cuda_arch_list: AutoArch, detected: T.List[str]) -> T.Tuple[T.List[str], T.List[str]]:
        """
        Using the CUDA Toolkit version and the target architectures, compute
        the NVCC architecture flags.
        """

        # arches the current nvcc supports
        cuda_supported_gpu_architectures: T.Set[str] = set()
        # arches you get when asking for 'All'
        cuda_known_gpu_architectures: T.Set[str] = set()
        # arches you get when asking for 'Common'
        cuda_common_gpu_architectures: T.Set[str] = set()
        # maximum common arch (used as the PTX saturation target)
        cuda_max_arch: str = '1.0'

        for arch, definition in _MICROISA_RANGES_DEF.items():
            if definition.supports(cuda_version):
                cuda_supported_gpu_architectures.add(arch)

                if arch.endswith('f'):
                    # don't want 'X.Yf' arches as part of any default collection
                    continue

                cuda_known_gpu_architectures.add(arch)

                if arch.endswith('a'):
                    # don't perform version comparisons on 'X.Ya' arches
                    continue

                if definition.common:
                    cuda_common_gpu_architectures.add(arch)

                    if Version(arch) > Version(cuda_max_arch):
                        cuda_max_arch = arch

        # need to add '+PTX' for the 'Common' collection
        cuda_common_gpu_architectures.add(cuda_max_arch + '+PTX')

        if not cuda_arch_list:
            cuda_arch_list = 'Auto'

        archs: T.Iterable[str]
        if   cuda_arch_list == 'All':     # noqa: E271
            archs = cuda_known_gpu_architectures
        elif cuda_arch_list == 'Common':  # noqa: E271
            archs = cuda_common_gpu_architectures
        elif cuda_arch_list == 'Auto':    # noqa: E271
            if detected:
                # a detected GPU newer than the toolkit supports can still JIT PTX
                # for the newest common arch -> saturate instead of dropping
                saturated: T.List[str] = []
                for arch in detected:
                    if _MICROISA_RE.fullmatch(arch) and Version(arch) > Version(cuda_max_arch):
                        saturated.append(cuda_max_arch + '+PTX')
                    else:
                        saturated.append(arch)
                archs = saturated
            else:
                archs = cuda_common_gpu_architectures
        elif isinstance(cuda_arch_list, str):
            archs = CudaModule._break_arch_string(cuda_arch_list)
        else:
            archs = cuda_arch_list

        # shared validation for the real and virtual halves of an 'X.Y(Z.W)' arch
        def isa_usable(isa: str, kind: str, arch: str) -> bool:
            isadef = _MICROISA_RANGES_DEF.get(isa, None)
            if isadef is None:
                raise InvalidArguments(f'Unknown CUDA {kind} in {arch}!')
            if isadef.cuda_too_old(cuda_version):
                mlog.warning(f'CUDA {cuda_version} is too old for architecture {isa}')
                return False
            if isadef.arch_too_old(cuda_version):
                mlog.warning(f'Architecture {isa} is too old for CUDA {cuda_version}')
                return False
            assert isa in cuda_supported_gpu_architectures
            return True

        # nvcc emits one SASS slot per GPU code and refuses to fill the same slot from
        # both a family-specific and a non family-specific arch ("The same GPU code
        # (`sm_121`) generated for non family-specific and family-specific GPU arch").
        # 'X.Yf' occupies the same slot as 'X.Y', while 'X.Ya' is a slot of its own.
        # slot -> (family-specific?, spec of first request, {(virtual, output), ...})
        cuda_arch_bin: T.Dict[str, T.Tuple[bool, str, T.Set[T.Tuple[Version, Version]]]] = {}
        # PTX is embedded per virtual arch and never occupies a SASS slot
        cuda_arch_ptx: T.Set[Version] = set()

        def add_bin_target(virtarch: str, outarch: str) -> None:
            slot = outarch.rstrip('f')
            family_specific = outarch.endswith('f') or virtarch.endswith('f')
            # remember how the slot was requested (in input syntax), so that a later
            # conflicting request can name both offenders in its error message
            spec = outarch if virtarch == outarch else f'{outarch}({virtarch})'
            if slot not in cuda_arch_bin:
                cuda_arch_bin[slot] = (family_specific, spec, set())
            elif cuda_arch_bin[slot][0] != family_specific:
                specs = ' and '.join(sorted((cuda_arch_bin[slot][1], spec)))
                gpu_code = 'sm_' + slot.replace('.', '')
                raise InvalidArguments(f'CUDA archs {specs} generate the same GPU code {gpu_code} from a family-specific and a non family-specific arch!')
            cuda_arch_bin[slot][2].add((Version(virtarch), Version(outarch)))

        for arch in archs:
            add_ptx = arch.endswith('+PTX')
            if add_ptx:
                arch = arch[:-len('+PTX')]

            if arch in _FAMILY_TO_MICROISAS:
                # something like 'Maxwell' or 'Ampere'
                # '(A)' arches have no forward compatibility, so embedding their PTX is meaningless
                if add_ptx and arch.endswith('(A)'):
                    raise InvalidArguments(f'CUDA arch {arch} and +PTX are mutually exclusive')

                isas = _FAMILY_TO_MICROISAS[arch]
                intersection = isas & cuda_supported_gpu_architectures
                if intersection:
                    for realarch in sorted(intersection):
                        virtarch = _MICROISA_RANGES_DEF[realarch].virt or realarch
                        add_bin_target(virtarch, realarch)
                    if add_ptx:
                        # we don't want PTX for things like 'Kepler+Tegra'
                        maxarch = max(intersection, key=Version)
                        virtarch = _MICROISA_RANGES_DEF[maxarch].virt or maxarch
                        cuda_arch_ptx.add(Version(virtarch))
                elif all(_MICROISA_RANGES_DEF[isa].cuda_too_old(cuda_version) for isa in isas):
                    mlog.warning(f'CUDA {cuda_version} is too old for {arch}')
                elif all(_MICROISA_RANGES_DEF[isa].arch_too_old(cuda_version) for isa in isas):
                    mlog.warning(f'{arch} is too old for CUDA {cuda_version}')
                else:
                    mlog.warning(f'{arch} is not supported by CUDA {cuda_version}')
            elif m := _ARCH_SPEC_RE.fullmatch(arch):
                # something like '12.0a' or '8.6(8.0)'
                realarch, virtarch = m.groups()

                # 'X.Ya' arches have no forward compatibility, so embedding their PTX is meaningless
                if add_ptx and (virtarch or realarch).endswith('a'):
                    raise InvalidArguments(f'CUDA arch {arch} and +PTX are mutually exclusive')

                # an architecture-specific 'X.Ya' virtual arch can only emit code for exactly 'X.Ya'
                # (nvcc: "Incompatible code generation requested")
                if virtarch and virtarch.endswith('a') and virtarch != realarch:
                    raise InvalidArguments(f'CUDA virtual arch {virtarch} is architecture-specific and can only pair with {virtarch} in {arch}!')

                if not isa_usable(realarch, 'Architecture', arch):
                    continue

                if virtarch:
                    if not isa_usable(virtarch, 'Virtual Architecture', arch):
                        continue
                    # an ISA carrying a virt override has no virtual form of its own (there is no compute_21)
                    redirect = _MICROISA_RANGES_DEF[virtarch].virt
                    if redirect is not None:
                        raise InvalidArguments(f'CUDA virtual arch {virtarch} does not exist in {arch}, use {redirect} instead!')

                    # nvcc pairing rules for suffixed arches ("Incompatible code generation requested"):
                    # - a family-specific 'X.Yf' virtual arch pairs only with members of its own
                    #   family generation that are at least as new as itself
                    # - a family-specific 'X.Yf' code arch requires a same-generation virtual arch
                    realbase = realarch.rstrip('af')
                    realfamily = _ISA_TO_FAMILY.get(realbase, 'unknown')
                    if virtarch.endswith('f'):
                        virtbase = virtarch.rstrip('f')
                        virtfamily = _ISA_TO_FAMILY.get(virtbase, 'unknown')
                        if (virtbase.split('.')[0] != realbase.split('.')[0]
                                or virtfamily != realfamily
                                or Version(realbase) < Version(virtbase)):
                            raise InvalidArguments(f'CUDA virtual arch {virtarch} ({virtfamily}) is family-specific and cannot pair with {realarch} ({realfamily}) in {arch}!')
                    elif realarch.endswith('f') and virtarch.split('.')[0] != realbase.split('.')[0]:
                        virtfamily = _ISA_TO_FAMILY.get(virtarch.rstrip('af'), 'unknown')
                        raise InvalidArguments(f'CUDA family-specific arch {realarch} ({realfamily}) requires a same-generation virtual arch, not {virtarch} ({virtfamily}), in {arch}!')
                else:
                    virtarch = _MICROISA_RANGES_DEF[realarch].virt or realarch

                add_bin_target(virtarch, realarch)
                if add_ptx:
                    cuda_arch_ptx.add(Version(virtarch))
            else:
                raise InvalidArguments(f'Unknown CUDA Architecture Name {arch}!')

        # the order we're looking for:
        # - 12.0a < 12.0f < 12.0
        #   by always appending 'z' to the Version, the vanilla '12.0' always goes last
        def version_key(v: Version) -> T.Tuple[T.Union[int, str], ...]:
            return (*v, 'z')

        bin_pairs: T.List[T.Tuple[Version, Version]] = [pair for _, _, pairs in cuda_arch_bin.values() for pair in pairs]

        # binary code for each requested arch, with the PTX fallbacks at the end
        gencode_flags: T.List[str] = []
        for virtual_target, output_target in sorted(bin_pairs, key=lambda p: (version_key(p[0]), version_key(p[1]))):
            virt = str(virtual_target).replace('.', '')
            output = str(output_target).replace('.', '')
            gencode_flags += ['-gencode', f'arch=compute_{virt},code=sm_{output}']
        for virtual_target in sorted(cuda_arch_ptx, key=version_key):
            virt = str(virtual_target).replace('.', '')
            gencode_flags += ['-gencode', f'arch=compute_{virt},code=compute_{virt}']

        arch_names: T.List[str] = []
        for _, output_target in sorted(bin_pairs, key=lambda p: version_key(p[1])):
            arch_names.append('sm_' + str(output_target).replace('.', ''))
        for virtual_target in sorted(cuda_arch_ptx, key=version_key):
            arch_names.append('compute_' + str(virtual_target).replace('.', ''))

        return gencode_flags, arch_names

def initialize(interp: Interpreter) -> CudaModule:
    return CudaModule(interp)
