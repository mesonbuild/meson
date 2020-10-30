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
from .hdf5 import hdf5_factory
from .base import (  # noqa: F401
    Dependency, DependencyException, DependencyMethods, ExternalProgram, EmptyExternalProgram, NonExistingExternalProgram,
    ExternalDependency, NotFoundDependency, ExternalLibrary, ExtraFrameworkDependency, InternalDependency,
    PkgConfigDependency, CMakeDependency, find_external_dependency, get_dep_identifier, packages, _packages_accept_language,
    DependencyFactory)
from .dev import ValgrindDependency, gmock_factory, gtest_factory, llvm_factory, zlib_factory
from .coarrays import coarray_factory
from .mpi import mpi_factory
from .scalapack import scalapack_factory
from .misc import (
    BlocksDependency, OpenMPDependency, cups_factory, curses_factory, gpgme_factory,
    libgcrypt_factory, libwmf_factory, netcdf_factory, pcap_factory, python3_factory,
    shaderc_factory, threads_factory,
)
from .platform import AppleFrameworks
from .ui import GnuStepDependency, Qt4Dependency, Qt5Dependency, WxDependency, gl_factory, sdl2_factory, vulkan_factory


# This is a dict where the keys should be strings, and the values must be one
# of:
# - An ExternalDependency subclass
# - A DependencyFactory object
# - A callable with a signature of (Environment, MachineChoice, Dict[str, Any]) -> List[Callable[[], DependencyType]]
packages.update({
    # From dev:
    'gtest': gtest_factory,
    'gmock': gmock_factory,
    'llvm': llvm_factory,
    'valgrind': ValgrindDependency,
    'zlib': zlib_factory,

    'boost': BoostDependency,
    'cuda': CudaDependency,

    # per-file
    'coarray': coarray_factory,
    'hdf5': hdf5_factory,
    'mpi': mpi_factory,
    'scalapack': scalapack_factory,

    # From misc:
    'blocks': BlocksDependency,
    'curses': curses_factory,
    'netcdf': netcdf_factory,
    'openmp': OpenMPDependency,
    'python3': python3_factory,
    'threads': threads_factory,
    'pcap': pcap_factory,
    'cups': cups_factory,
    'libwmf': libwmf_factory,
    'libgcrypt': libgcrypt_factory,
    'gpgme': gpgme_factory,
    'shaderc': shaderc_factory,

    # From platform:
    'appleframeworks': AppleFrameworks,

    # From ui:
    'gl': gl_factory,
    'gnustep': GnuStepDependency,
    'qt4': Qt4Dependency,
    'qt5': Qt5Dependency,
    'sdl2': sdl2_factory,
    'wxwidgets': WxDependency,
    'vulkan': vulkan_factory,
})
_packages_accept_language.update({
    'hdf5',
    'mpi',
    'netcdf',
    'openmp',
})
