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

from .base import (  # noqa: F401
    Dependency, DependencyException, DependencyMethods, ExternalProgram,
    ExternalDependency, ExternalLibrary, ExtraFrameworkDependency, InternalDependency,
    PkgConfigDependency, find_external_dependency, get_dep_identifier, packages)
from .dev import GMockDependency, GTestDependency, LLVMDependency, ValgrindDependency
from .misc import BoostDependency, Python3Dependency, ThreadDependency
from .platform import AppleFrameworks
from .ui import GLDependency, GnuStepDependency, Qt4Dependency, Qt5Dependency, SDL2Dependency, WxDependency


packages.update({
    # From dev:
    'gtest': GTestDependency,
    'gmock': GMockDependency,
    'llvm': LLVMDependency,
    'valgrind': ValgrindDependency,

    # From misc:
    'boost': BoostDependency,
    'python3': Python3Dependency,
    'threads': ThreadDependency,

    # From platform:
    'appleframeworks': AppleFrameworks,

    # From ui:
    'gl': GLDependency,
    'gnustep': GnuStepDependency,
    'qt4': Qt4Dependency,
    'qt5': Qt5Dependency,
    'sdl2': SDL2Dependency,
    'wxwidgets': WxDependency,
})
