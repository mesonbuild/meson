# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Marco Rebhan <me@dblsaiko.net>

from __future__ import annotations

import typing as T

from . import NewExtensionModule, ModuleInfo, ModuleReturnValue
from mesonbuild import build, dependencies
from mesonbuild.interpreter.type_checking import KwargInfo, NoneType
from mesonbuild.interpreterbase.decorators import ContainerTypeInfo, FeatureNew, typed_kwargs, typed_pos_args
from mesonbuild.nsbundle import BundleType

if T.TYPE_CHECKING:
    from typing_extensions import TypedDict

    from . import ModuleState
    from mesonbuild.interpreter import Interpreter

    class CommonKws(TypedDict):
        contents: T.Optional[build.StructuredSources]
        resources: T.Optional[build.StructuredSources]
        extra_binaries: T.List[T.Union[str, build.File, build.Executable, build.CustomTarget, build.CustomTargetIndex]]
        info_plist: T.Optional[T.Union[str, build.File, build.CustomTarget, build.CustomTargetIndex]]

    class ApplicationKws(CommonKws):
        layout: T.Optional[str]
        executable_folder_name: T.Optional[str]

    class FrameworkKws(CommonKws):
        headers: T.Optional[build.StructuredSources]


COMMON_KWS: T.List[KwargInfo] = [
    KwargInfo('contents', (NoneType, build.StructuredSources)),
    KwargInfo('resources', (NoneType, build.StructuredSources)),
    KwargInfo('extra_binaries', ContainerTypeInfo(list, (str, build.File, build.Executable, build.CustomTarget,
                                                         build.CustomTargetIndex)), default=[], listify=True),
    KwargInfo('info_plist', (NoneType, str, build.File, build.CustomTarget, build.CustomTargetIndex))
]

APPLICATION_KWS: T.List[KwargInfo] = [
    *COMMON_KWS,
    KwargInfo('layout', (NoneType, str)),
    KwargInfo('executable_folder_name', (NoneType, str)),
]

FRAMEWORK_KWS: T.List[KwargInfo] = [
    *COMMON_KWS,
    KwargInfo('headers', (NoneType, build.StructuredSources)),
]


def initialize(*args: T.Any, **kwargs: T.Any) -> NSBundleModule:
    return NSBundleModule(*args, **kwargs)


class NSBundleModule(NewExtensionModule):
    INFO = ModuleInfo('nsbundle', '1.7.99')

    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.methods.update({
            'wrap_application': self.wrap_application,
            'wrap_framework': self.wrap_framework,
        })

    @FeatureNew('nsbundle.wrap_application', '1.7.99')
    @typed_pos_args('nsbundle.wrap_application', build.Executable)
    @typed_kwargs('nsbundle.wrap_application', *APPLICATION_KWS)
    def wrap_application(self, state: ModuleState, args: T.Tuple[build.Executable], kwargs: ApplicationKws
                         ) -> ModuleReturnValue:
        (main_exe,) = args

        tgt = build.BundleTarget(main_exe.name, state.subdir, state.subproject, state.environment, main_exe, BundleType.APPLICATION)
        tgt.bundle_info.resources = kwargs['resources']
        tgt.bundle_info.contents = kwargs['contents']
        tgt.bundle_info.extra_binaries = kwargs['extra_binaries']

        if kwargs['info_plist'] is not None:
            tgt.bundle_info.info_dict_file = build._source_input_to_file(tgt, 'info_plist', kwargs['info_plist'])

        return ModuleReturnValue(tgt, [tgt])

    @FeatureNew('nsbundle.wrap_framework', '1.7.99')
    @typed_pos_args('nsbundle.wrap_framework', (build.SharedLibrary, dependencies.InternalDependency))
    @typed_kwargs('nsbundle.wrap_framework', *FRAMEWORK_KWS)
    def wrap_framework(self, state: ModuleState,
                       args: T.Tuple[T.Union[build.SharedLibrary, dependencies.InternalDependency]],
                       kwargs: FrameworkKws) -> ModuleReturnValue:
        (main_lib,) = args

        # TODO
        if not isinstance(main_lib, dependencies.InternalDependency):
            main_lib = dependencies.InternalDependency(state.project_version, [], [], [], [main_lib], [], [], [], [],
                                                       {}, [], [], [])

        return ModuleReturnValue(main_lib, [])
