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

# Public symbols for compilers sub-package when using 'from . import compilers'
__all__ = [
    'CLANG_OSX',
    'CLANG_STANDARD',
    'CLANG_WIN',
    'GCC_CYGWIN',
    'GCC_MINGW',
    'GCC_OSX',
    'GCC_STANDARD',
    'ICC_OSX',
    'ICC_STANDARD',
    'ICC_WIN',

    'all_languages',
    'base_options',
    'clike_langs',
    'c_suffixes',
    'cpp_suffixes',
    'get_macos_dylib_install_name',
    'get_base_compile_args',
    'get_base_link_args',
    'is_assembly',
    'is_header',
    'is_library',
    'is_llvm_ir',
    'is_object',
    'is_source',
    'lang_suffixes',
    'sanitizer_compile_args',
    'sort_clike',

    'ArmCCompiler',
    'ArmCPPCompiler',
    'CCompiler',
    'ClangCCompiler',
    'ClangCompiler',
    'ClangCPPCompiler',
    'ClangObjCCompiler',
    'ClangObjCPPCompiler',
    'CompilerArgs',
    'CPPCompiler',
    'DCompiler',
    'DmdDCompiler',
    'FortranCompiler',
    'G95FortranCompiler',
    'GnuCCompiler',
    'ElbrusCCompiler',
    'GnuCompiler',
    'GnuCPPCompiler',
    'ElbrusCPPCompiler',
    'GnuDCompiler',
    'GnuFortranCompiler',
    'ElbrusFortranCompiler',
    'GnuObjCCompiler',
    'GnuObjCPPCompiler',
    'IntelCompiler',
    'IntelCCompiler',
    'IntelCPPCompiler',
    'IntelFortranCompiler',
    'JavaCompiler',
    'LLVMDCompiler',
    'MonoCompiler',
    'VisualStudioCsCompiler',
    'NAGFortranCompiler',
    'ObjCCompiler',
    'ObjCPPCompiler',
    'Open64FortranCompiler',
    'PathScaleFortranCompiler',
    'PGIFortranCompiler',
    'RustCompiler',
    'SunFortranCompiler',
    'SwiftCompiler',
    'ValaCompiler',
    'VisualStudioCCompiler',
    'VisualStudioCPPCompiler',
]

# Bring symbols from each module into compilers sub-package namespace
from .compilers import (
    GCC_OSX,
    GCC_MINGW,
    GCC_CYGWIN,
    GCC_STANDARD,
    CLANG_OSX,
    CLANG_WIN,
    CLANG_STANDARD,
    ICC_OSX,
    ICC_WIN,
    ICC_STANDARD,
    all_languages,
    base_options,
    clike_langs,
    c_suffixes,
    cpp_suffixes,
    get_macos_dylib_install_name,
    get_base_compile_args,
    get_base_link_args,
    is_header,
    is_source,
    is_assembly,
    is_llvm_ir,
    is_object,
    is_library,
    lang_suffixes,
    sanitizer_compile_args,
    sort_clike,
    ClangCompiler,
    CompilerArgs,
    GnuCompiler,
    IntelCompiler,
)
from .c import (
    ArmCCompiler,
    CCompiler,
    ClangCCompiler,
    GnuCCompiler,
    ElbrusCCompiler,
    IntelCCompiler,
    VisualStudioCCompiler,
)
from .cpp import (
    ArmCPPCompiler,
    CPPCompiler,
    ClangCPPCompiler,
    GnuCPPCompiler,
    ElbrusCPPCompiler,
    IntelCPPCompiler,
    VisualStudioCPPCompiler,
)
from .cs import MonoCompiler, VisualStudioCsCompiler
from .d import (
    DCompiler,
    DmdDCompiler,
    GnuDCompiler,
    LLVMDCompiler,
)
from .fortran import (
    FortranCompiler,
    G95FortranCompiler,
    GnuFortranCompiler,
    ElbrusFortranCompiler,
    IntelFortranCompiler,
    NAGFortranCompiler,
    Open64FortranCompiler,
    PathScaleFortranCompiler,
    PGIFortranCompiler,
    SunFortranCompiler,
)
from .java import JavaCompiler
from .objc import (
    ObjCCompiler,
    ClangObjCCompiler,
    GnuObjCCompiler,
)
from .objcpp import (
    ObjCPPCompiler,
    ClangObjCPPCompiler,
    GnuObjCPPCompiler,
)
from .rust import RustCompiler
from .swift import SwiftCompiler
from .vala import ValaCompiler
