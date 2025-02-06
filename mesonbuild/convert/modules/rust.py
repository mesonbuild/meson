# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import typing as T
import os

from mesonbuild.build import BuildTarget, CustomTarget, CustomTargetIndex, GeneratedList
from mesonbuild.interpreterbase import InterpreterException, noKwargs, noPosargs, typed_kwargs
from mesonbuild.convert.convert_project_instance import ConvertProjectInstance
from mesonbuild.convert.instance.convert_instance_utils import ConvertId, ConvertInstanceRustBindgen
from mesonbuild.modules import ModuleReturnValue, ModuleState
from mesonbuild.mesonlib import File
from mesonbuild.modules.rust import RustModule, BINDGEN_KWS

if T.TYPE_CHECKING:
    from mesonbuild.interpreterbase import TYPE_kwargs
    from mesonbuild.modules.rust import FuncBindgen
    from mesonbuild.convert.convert_interpreter import ConvertInterpreter


class ConvertRustModule(RustModule):
    """Custom Rust module for the convert tool.  Mainly useful for bindgen."""

    def __init__(self, interpreter: ConvertInterpreter, project_instance: ConvertProjectInstance) -> None:  # fmt: skip
        super().__init__(interpreter)
        self.project_instance = project_instance
        self.methods.update({'bindgen': self.bindgen, 'cbindgen': self.cbindgen})

    @noPosargs
    @typed_kwargs('rust.bindgen', *BINDGEN_KWS)
    def bindgen(self, state: ModuleState, args: T.List, kwargs: FuncBindgen) -> ModuleReturnValue:
        _header, *_deps = kwargs['input']
        input_file = self.interpreter.source_strings_to_files([_header])[0]
        if isinstance(input_file, (BuildTarget, CustomTarget, CustomTargetIndex, GeneratedList)):
            subdir, filename = os.path.split(input_file.get_outputs()[0])
            input_file = File.from_source_file(self.project_instance.project_dir, subdir, filename)  # noqa #fmt: skip
        elif not isinstance(input_file, File):
            raise InterpreterException(
                f'Invalid input type {type(input_file).__name__} for bindgen'
            )

        name = os.path.basename(input_file.fname)
        crate_name = f'{name}_bindgen_internal'.replace('.', '_')
        (fg_name, subdir) = self.project_instance.determine_filegroup(input_file)
        src = ConvertId(fg_name, subdir)

        convert_bindgen = ConvertInstanceRustBindgen(
            crate_name, state.subdir, src, args=kwargs['args'], output=kwargs['output']
        )
        self.project_instance.add_rust_bindgen(convert_bindgen)
        return ModuleReturnValue(convert_bindgen, [convert_bindgen])

    @noPosargs
    @noKwargs
    def cbindgen(self, state: ModuleState, args: T.List, kwargs: TYPE_kwargs) -> ModuleReturnValue:
        raise InterpreterException('rust.cbindgen is not supported by the convert tool')
