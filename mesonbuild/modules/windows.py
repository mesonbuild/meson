# SPDX-License-Identifier: Apache-2.0
# Copyright 2015 The Meson development team

from __future__ import annotations

import typing as T


from . import ExtensionModule, ModuleInfo
from . import ModuleReturnValue
from .. import mesonlib, build
from .. import mlog
from ..interpreter.type_checking import DEPEND_FILES_KW, DEPENDS_KW, INCLUDE_DIRECTORIES
from ..interpreterbase.decorators import ContainerTypeInfo, KwargInfo, typed_kwargs, typed_pos_args
from ..mesonlib import MachineChoice

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter import Interpreter

    from typing_extensions import TypedDict

    class CompileResources(TypedDict):

        depend_files: T.List[mesonlib.FileOrString]
        depends: T.List[T.Union[build.BuildTarget, build.CustomTarget]]
        include_directories: T.List[T.Union[str, build.IncludeDirs]]
        implicit_include_directories: bool
        args: T.List[str]


class WindowsModule(ExtensionModule):

    INFO = ModuleInfo('windows')

    def __init__(self, interpreter: 'Interpreter'):
        super().__init__(interpreter)
        self.methods.update({
            'compile_resources': self.compile_resources,
        })

    @typed_pos_args('windows.compile_resources', varargs=(str, mesonlib.File, build.CustomTarget, build.CustomTargetIndex), min_varargs=1)
    @typed_kwargs(
        'windows.compile_resources',
        DEPEND_FILES_KW.evolve(since='0.47.0'),
        DEPENDS_KW.evolve(since='0.47.0'),
        INCLUDE_DIRECTORIES,
        KwargInfo('implicit_include_directories', bool, default=False, since='1.11.0'),
        KwargInfo('args', ContainerTypeInfo(list, str), default=[], listify=True),
    )
    def compile_resources(self, state: 'ModuleState',
                          args: T.Tuple[T.List[T.Union[str, mesonlib.File, build.CustomTarget, build.CustomTargetIndex]]],
                          kwargs: 'CompileResources') -> ModuleReturnValue:
        mlog.deprecation('windows.compile_resources() is deprecated, '
                         'Meson now has support for the \'rc\' language. '
                         'pass .rc files directly to build targets instead.',
                         location=state.current_node)

        if kwargs['depend_files']:
            mlog.warning('windows.compile_resources() depend_files is ignored, '
                         'pass depend_files to the build target instead.',
                         location=state.current_node)

        # Ensure the 'rc' language is detected so the normal compile pipeline
        # can handle .rc files.
        state.add_language('rc', MachineChoice.HOST)

        # Inject args and include_directories into project args for the rc
        # language, so the normal compile pipeline picks them up.
        extra_args = kwargs['args'].copy()
        extra_args += state.get_include_args(
            kwargs['include_directories'], kwargs['implicit_include_directories'])
        if extra_args:
            rc_args = state.project_args.get('rc', [])
            state.project_args['rc'] = rc_args + extra_args

        # Convert string sources to File objects; pass through
        # CustomTarget/CustomTargetIndex as-is (they are generated .rc files).
        sources: T.List[T.Union[mesonlib.File, build.CustomTarget, build.CustomTargetIndex, build.BuildTarget]] = []
        for src in args[0]:
            if isinstance(src, str):
                sources.append(mesonlib.File.from_source_file(
                    state.environment.source_dir, state.subdir, src))
            else:
                sources.append(src)

        # Pass through depends so the build target has proper ordering
        # dependencies (e.g. a custom_target that generates an icon file
        # referenced by the .rc source).
        for dep in kwargs['depends']:
            sources.append(dep)

        return ModuleReturnValue(sources, [])

def initialize(interp: 'Interpreter') -> WindowsModule:
    return WindowsModule(interp)
