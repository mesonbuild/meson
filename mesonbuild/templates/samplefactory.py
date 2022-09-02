# Copyright 2019 The Meson development team

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
import typing as T

from ..templates.valatemplates import ValaProject
from ..templates.fortrantemplates import FortranProject
from ..templates.objcpptemplates import ObjCppProject
from ..templates.dlangtemplates import DlangProject
from ..templates.rusttemplates import RustProject
from ..templates.javatemplates import JavaProject
from ..templates.cudatemplates import CudaProject
from ..templates.objctemplates import ObjCProject
from ..templates.cpptemplates import CppProject
from ..templates.cstemplates import CSharpProject
from ..templates.ctemplates import CProject

if T.TYPE_CHECKING:
    import argparse

    from ..templates.sampleimpl import SampleImpl


def sameple_generator(options: argparse.Namespace) -> SampleImpl:
    return {
        'c': CProject,
        'cpp': CppProject,
        'cs': CSharpProject,
        'cuda': CudaProject,
        'objc': ObjCProject,
        'objcpp': ObjCppProject,
        'java': JavaProject,
        'd': DlangProject,
        'rust': RustProject,
        'fortran': FortranProject,
        'vala': ValaProject
    }[options.language](options)
