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

from mesonbuild.templates.valatemplates import ValaProject
from mesonbuild.templates.fortrantemplates import FortranProject
from mesonbuild.templates.objcpptemplates import ObjCppProject
from mesonbuild.templates.dlangtemplates import DlangProject
from mesonbuild.templates.rusttemplates import RustProject
from mesonbuild.templates.javatemplates import JavaProject
from mesonbuild.templates.cudatemplates import CudaProject
from mesonbuild.templates.objctemplates import ObjCProject
from mesonbuild.templates.cpptemplates import CppProject
from mesonbuild.templates.cstemplates import CSharpProject
from mesonbuild.templates.ctemplates import CProject

if T.TYPE_CHECKING:
    from ..minit import Arguments
    from .sampleimpl import ClassImpl, FileHeaderImpl, FileImpl, SampleImpl


_IMPL: T.Mapping[str, T.Union[T.Type[ClassImpl], T.Type[FileHeaderImpl], T.Type[FileImpl]]] = {
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
    'vala': ValaProject,
}


def sample_generator(options: Arguments) -> SampleImpl:
    return _IMPL[options.language](options)
