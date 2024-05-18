# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 The Meson development team

from __future__ import annotations

import typing as T

# Import the templates for different programming languages
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

# Import the Arguments and SampleImpl types
if T.TYPE_CHECKING:
    from ..minit import Arguments
    from .sampleimpl import ClassImpl, FileHeaderImpl, FileImpl, SampleImpl

# Mapping of programming languages to corresponding template classes
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
    """
    Generate a sample implementation based on the provided options.

    Args:
        options (Arguments): The options specifying the project type and language.

    Returns:
        SampleImpl: An instance of a sample implementation based on the provided options.
    """
    # Retrieve the appropriate template class based on the language specified in the options
    template_class = _IMPL[options.language]

    # Instantiate the template class with the provided options and return the instance
    return template_class(options)
