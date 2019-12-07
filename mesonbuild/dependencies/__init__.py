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

from .boost import BoostDependency
from .cuda import CudaDependency
from .hdf5 import HDF5Dependency
from .base import (  # noqa: F401
    Dependency, DependencyException, DependencyMethods, ExternalProgram, EmptyExternalProgram, NonExistingExternalProgram,
    ExternalDependency, NotFoundDependency, ExternalLibrary, ExtraFrameworkDependency, InternalDependency,
    PkgConfigDependency, CMakeDependency, find_external_dependency, get_dep_identifier, packages, _packages_accept_language)
from .dev import GMockDependency, GTestDependency, LLVMDependency, ValgrindDependency
from .coarrays import CoarrayDependency
from .mpi import MPIDependency
from .scalapack import ScalapackDependency
from .misc import (BlocksDependency, NetCDFDependency, OpenMPDependency, Python3Dependency, ThreadDependency, PcapDependency, CupsDependency, LibWmfDependency, LibGCryptDependency, GpgmeDependency, ShadercDependency)
from .platform import AppleFrameworks
from .ui import GLDependency, GnuStepDependency, Qt4Dependency, Qt5Dependency, SDL2Dependency, WxDependency, VulkanDependency


packages.update({
    # From dev:
    'gtest': GTestDependency,
    'gmock': GMockDependency,
    'llvm': LLVMDependency,
    'valgrind': ValgrindDependency,

    'boost': BoostDependency,
    'cuda': CudaDependency,

    # per-file
    'coarray': CoarrayDependency,
    'hdf5': HDF5Dependency,
    'mpi': MPIDependency,
    'scalapack': ScalapackDependency,

    # From misc:
    'blocks': BlocksDependency,
    'netcdf': NetCDFDependency,
    'openmp': OpenMPDependency,
    'python3': Python3Dependency,
    'threads': ThreadDependency,
    'pcap': PcapDependency,
    'cups': CupsDependency,
    'libwmf': LibWmfDependency,
    'libgcrypt': LibGCryptDependency,
    'gpgme': GpgmeDependency,
    'shaderc': ShadercDependency,

    # From platform:
    'appleframeworks': AppleFrameworks,

    # From ui:
    'gl': GLDependency,
    'gnustep': GnuStepDependency,
    'qt4': Qt4Dependency,
    'qt5': Qt5Dependency,
    'sdl2': SDL2Dependency,
    'wxwidgets': WxDependency,
    'vulkan': VulkanDependency,
})
_packages_accept_language.update({
    'hdf5',
    'mpi',
    'netcdf',
    'openmp',
})
