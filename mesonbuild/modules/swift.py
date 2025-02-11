# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Meson development team

from __future__ import annotations

import typing as T

from . import NewExtensionModule, ModuleInfo, ModuleReturnValue
from mesonbuild import build
from mesonbuild.compilers.swift import SwiftCompiler
from mesonbuild.interpreterbase.decorators import typed_kwargs, typed_pos_args

if T.TYPE_CHECKING:
    from . import ModuleState
    from mesonbuild.interpreter import Interpreter


def initialize(*args: T.Any, **kwargs: T.Any) -> SwiftModule:
    return SwiftModule(*args, **kwargs)


class SwiftModule(NewExtensionModule):
    INFO = ModuleInfo('swift', '1.7.99')

    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.interpreter = interpreter
        self.swiftc: T.Optional[SwiftCompiler]

        try:
            swiftc = interpreter.compilers.host['swift']
            assert isinstance(swiftc, SwiftCompiler), 'swiftc is not an instance of SwiftCompiler'
            self.swiftc = swiftc
        except KeyError:
            self.swiftc = None

        self.methods.update({
            'generate_cpp_header': self.generate_cpp_header,
        })

    @typed_pos_args('swift.generate_cpp_header', build.BuildTarget)
    @typed_kwargs('swift.generate_cpp_header')
    def generate_cpp_header(self, state: ModuleState, args: T.Tuple[build.BuildTarget], kwargs) -> ModuleReturnValue:
        (module,) = args

        header_name = f'{module.name}-Swift.h'
        command = [
            *self.swiftc.get_exelist(),
            '@INPUT@',
            *self.swiftc.get_module_args(module.name),
            *self.swiftc.get_cxx_interoperability_args(self.interpreter.compilers.host),
            '-emit-clang-header-path', '@OUTPUT@',
        ]

        tgt = build.CustomTarget(header_name, state.subdir, state.subproject, state.environment, command,
                                 module.get_sources() + module.get_generated_sources(), [header_name],
                                 backend=state.backend)

        return ModuleReturnValue(tgt, [tgt])
