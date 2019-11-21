# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from ..mesonlib import version_compare
from ..interpreter import CompilerHolder
from ..compilers import CudaCompiler

from . import ExtensionModule, ModuleReturnValue

from ..interpreterbase import (
    flatten, permittedKwargs, noKwargs,
    InvalidArguments, FeatureNew
)

class CudaModule(ExtensionModule):

    @FeatureNew('CUDA module', '0.50.0')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @noKwargs
    def min_driver_version(self, state, args, kwargs):
        argerror = InvalidArguments('min_driver_version must have exactly one positional argument: ' +
                                    'an NVCC compiler object, or its version string.')

        if len(args) != 1:
            raise argerror
        else:
            cuda_version = self._version_from_compiler(args[0])
            if cuda_version == 'unknown':
                raise argerror

        driver_version_table = [
            {'cuda_version': '>=10.2.89',  'windows': '441.22', 'linux': '440.33'},
            {'cuda_version': '>=10.1.105', 'windows': '418.96', 'linux': '418.39'},
            {'cuda_version': '>=10.0.130', 'windows': '411.31', 'linux': '410.48'},
            {'cuda_version': '>=9.2.148',  'windows': '398.26', 'linux': '396.37'},
            {'cuda_version': '>=9.2.88',   'windows': '397.44', 'linux': '396.26'},
            {'cuda_version': '>=9.1.85',   'windows': '391.29', 'linux': '390.46'},
            {'cuda_version': '>=9.0.76',   'windows': '385.54', 'linux': '384.81'},
            {'cuda_version': '>=8.0.61',   'windows': '376.51', 'linux': '375.26'},
            {'cuda_version': '>=8.0.44',   'windows': '369.30', 'linux': '367.48'},
            {'cuda_version': '>=7.5.16',   'windows': '353.66', 'linux': '352.31'},
            {'cuda_version': '>=7.0.28',   'windows': '347.62', 'linux': '346.46'},
        ]

        driver_version = 'unknown'
        for d in driver_version_table:
            if version_compare(cuda_version, d['cuda_version']):
                driver_version = d.get(state.host_machine.system, d['linux'])
                break

        return ModuleReturnValue(driver_version, [driver_version])

    @permittedKwargs(['detected'])
    def nvcc_arch_flags(self, state, args, kwargs):
        nvcc_arch_args = self._validate_nvcc_arch_args(state, args, kwargs)
        ret = self._nvcc_arch_flags(*nvcc_arch_args)[0]
        return ModuleReturnValue(ret, [ret])

    @permittedKwargs(['detected'])
    def nvcc_arch_readable(self, state, args, kwargs):
        nvcc_arch_args = self._validate_nvcc_arch_args(state, args, kwargs)
        ret = self._nvcc_arch_flags(*nvcc_arch_args)[1]
        return ModuleReturnValue(ret, [ret])

    @staticmethod
    def _break_arch_string(s):
        s = re.sub('[ \t\r\n,;]+', ';', s)
        s = s.strip(';').split(';')
        return s

    @staticmethod
    def _detected_cc_from_compiler(c):
        if isinstance(c, CompilerHolder):
            c = c.compiler
        if isinstance(c, CudaCompiler):
            return c.detected_cc
        return ''

    @staticmethod
    def _version_from_compiler(c):
        if isinstance(c, CompilerHolder):
            c = c.compiler
        if isinstance(c, CudaCompiler):
            return c.version
        if isinstance(c, str):
            return c
        return 'unknown'

    def _validate_nvcc_arch_args(self, state, args, kwargs):
        argerror = InvalidArguments('The first argument must be an NVCC compiler object, or its version string!')

        if len(args) < 1:
            raise argerror
        else:
            compiler = args[0]
            cuda_version = self._version_from_compiler(compiler)
            if cuda_version == 'unknown':
                raise argerror

        arch_list = [] if len(args) <= 1 else flatten(args[1:])
        arch_list = [self._break_arch_string(a) for a in arch_list]
        arch_list = flatten(arch_list)
        if len(arch_list) > 1 and not set(arch_list).isdisjoint({'All', 'Common', 'Auto'}):
            raise InvalidArguments('''The special architectures 'All', 'Common' and 'Auto' must appear alone, as a positional argument!''')
        arch_list = arch_list[0] if len(arch_list) == 1 else arch_list

        detected = kwargs.get('detected', self._detected_cc_from_compiler(compiler))
        detected = flatten([detected])
        detected = [self._break_arch_string(a) for a in detected]
        detected = flatten(detected)
        if not set(detected).isdisjoint({'All', 'Common', 'Auto'}):
            raise InvalidArguments('''The special architectures 'All', 'Common' and 'Auto' must appear alone, as a positional argument!''')

        return cuda_version, arch_list, detected

    def _nvcc_arch_flags(self, cuda_version, cuda_arch_list='Auto', detected=''):
        """
        Using the CUDA Toolkit version (the NVCC version) and the target
        architectures, compute the NVCC architecture flags.
        """

        cuda_known_gpu_architectures  = ['Fermi', 'Kepler', 'Maxwell']  # noqa: E221
        cuda_common_gpu_architectures = ['3.0', '3.5', '5.0']           # noqa: E221
        cuda_limit_gpu_architecture   = None                            # noqa: E221
        cuda_all_gpu_architectures    = ['3.0', '3.2', '3.5', '5.0']    # noqa: E221

        if version_compare(cuda_version, '<7.0'):
            cuda_limit_gpu_architecture = '5.2'

        if version_compare(cuda_version, '>=7.0'):
            cuda_known_gpu_architectures  += ['Kepler+Tegra', 'Kepler+Tesla', 'Maxwell+Tegra']  # noqa: E221
            cuda_common_gpu_architectures += ['5.2']                                            # noqa: E221

            if version_compare(cuda_version, '<8.0'):
                cuda_common_gpu_architectures += ['5.2+PTX']  # noqa: E221
                cuda_limit_gpu_architecture    = '6.0'        # noqa: E221

        if version_compare(cuda_version, '>=8.0'):
            cuda_known_gpu_architectures  += ['Pascal', 'Pascal+Tegra']  # noqa: E221
            cuda_common_gpu_architectures += ['6.0', '6.1']              # noqa: E221
            cuda_all_gpu_architectures    += ['6.0', '6.1', '6.2']       # noqa: E221

            if version_compare(cuda_version, '<9.0'):
                cuda_common_gpu_architectures += ['6.1+PTX']  # noqa: E221
                cuda_limit_gpu_architecture    = '7.0'        # noqa: E221

        if version_compare(cuda_version, '>=9.0'):
            cuda_known_gpu_architectures  += ['Volta', 'Xavier']                   # noqa: E221
            cuda_common_gpu_architectures += ['7.0', '7.0+PTX']                    # noqa: E221
            cuda_all_gpu_architectures    += ['7.0', '7.0+PTX', '7.2', '7.2+PTX']  # noqa: E221

            if version_compare(cuda_version, '<10.0'):
                cuda_limit_gpu_architecture = '7.5'

        if version_compare(cuda_version, '>=10.0'):
            cuda_known_gpu_architectures  += ['Turing']          # noqa: E221
            cuda_common_gpu_architectures += ['7.5', '7.5+PTX']  # noqa: E221
            cuda_all_gpu_architectures    += ['7.5', '7.5+PTX']  # noqa: E221

            if version_compare(cuda_version, '<11.0'):
                cuda_limit_gpu_architecture = '8.0'

        if not cuda_arch_list:
            cuda_arch_list = 'Auto'

        if   cuda_arch_list == 'All':     # noqa: E271
            cuda_arch_list = cuda_known_gpu_architectures
        elif cuda_arch_list == 'Common':  # noqa: E271
            cuda_arch_list = cuda_common_gpu_architectures
        elif cuda_arch_list == 'Auto':    # noqa: E271
            if detected:
                if isinstance(detected, list):
                    cuda_arch_list = detected
                else:
                    cuda_arch_list = self._break_arch_string(detected)

                if cuda_limit_gpu_architecture:
                    filtered_cuda_arch_list = []
                    for arch in cuda_arch_list:
                        if arch:
                            if version_compare(arch, '>=' + cuda_limit_gpu_architecture):
                                arch = cuda_common_gpu_architectures[-1]
                            if arch not in filtered_cuda_arch_list:
                                filtered_cuda_arch_list.append(arch)
                    cuda_arch_list = filtered_cuda_arch_list
            else:
                cuda_arch_list = cuda_common_gpu_architectures
        elif isinstance(cuda_arch_list, str):
            cuda_arch_list = self._break_arch_string(cuda_arch_list)

        cuda_arch_list = sorted([x for x in set(cuda_arch_list) if x])

        cuda_arch_bin = []
        cuda_arch_ptx = []
        for arch_name in cuda_arch_list:
            arch_bin = []
            arch_ptx = []
            add_ptx = arch_name.endswith('+PTX')
            if add_ptx:
                arch_name = arch_name[:-len('+PTX')]

            if re.fullmatch('[0-9]+\\.[0-9](\\([0-9]+\\.[0-9]\\))?', arch_name):
                arch_bin, arch_ptx = [arch_name], [arch_name]
            else:
                arch_bin, arch_ptx = {
                    'Fermi':         (['2.0', '2.1(2.0)'], []),
                    'Kepler+Tegra':  (['3.2'],             []),
                    'Kepler+Tesla':  (['3.7'],             []),
                    'Kepler':        (['3.0', '3.5'],      ['3.5']),
                    'Maxwell+Tegra': (['5.3'],             []),
                    'Maxwell':       (['5.0', '5.2'],      ['5.2']),
                    'Pascal':        (['6.0', '6.1'],      ['6.1']),
                    'Pascal+Tegra':  (['6.2'],             []),
                    'Volta':         (['7.0'],             ['7.0']),
                    'Xavier':        (['7.2'],             []),
                    'Turing':        (['7.5'],             ['7.5']),
                }.get(arch_name, (None, None))

            if arch_bin is None:
                raise InvalidArguments('Unknown CUDA Architecture Name {}!'
                                       .format(arch_name))

            cuda_arch_bin += arch_bin

            if add_ptx:
                if not arch_ptx:
                    arch_ptx = arch_bin
                cuda_arch_ptx += arch_ptx

        cuda_arch_bin = re.sub('\\.', '', ' '.join(cuda_arch_bin))
        cuda_arch_ptx = re.sub('\\.', '', ' '.join(cuda_arch_ptx))
        cuda_arch_bin = re.findall('[0-9()]+', cuda_arch_bin)
        cuda_arch_ptx = re.findall('[0-9]+',   cuda_arch_ptx)
        cuda_arch_bin = sorted(list(set(cuda_arch_bin)))
        cuda_arch_ptx = sorted(list(set(cuda_arch_ptx)))

        nvcc_flags = []
        nvcc_archs_readable = []

        for arch in cuda_arch_bin:
            m = re.match('([0-9]+)\\(([0-9]+)\\)', arch)
            if m:
                nvcc_flags += ['-gencode', 'arch=compute_' + m[2] + ',code=sm_' + m[1]]
                nvcc_archs_readable += ['sm_' + m[1]]
            else:
                nvcc_flags += ['-gencode', 'arch=compute_' + arch + ',code=sm_' + arch]
                nvcc_archs_readable += ['sm_' + arch]

        for arch in cuda_arch_ptx:
            nvcc_flags += ['-gencode', 'arch=compute_' + arch + ',code=compute_' + arch]
            nvcc_archs_readable += ['compute_' + arch]

        return nvcc_flags, nvcc_archs_readable

def initialize(*args, **kwargs):
    return CudaModule(*args, **kwargs)
