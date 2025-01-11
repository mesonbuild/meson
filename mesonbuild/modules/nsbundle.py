# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 Marco Rebhan <me@dblsaiko.net>

from __future__ import annotations

import typing as T

from . import NewExtensionModule, ModuleInfo, ModuleReturnValue
from mesonbuild.build import AppBundle, FrameworkBundle
from mesonbuild.interpreter.type_checking import NSAPP_KWS, NSFRAMEWORK_KWS, SOURCES_VARARGS
from mesonbuild.interpreterbase.decorators import FeatureNew, typed_kwargs, typed_pos_args

if T.TYPE_CHECKING:
    from . import ModuleState
    from mesonbuild.interpreter.type_checking import SourcesVarargsType
    from mesonbuild.interpreter import Interpreter, kwargs as kwtypes


def initialize(*args: T.Any, **kwargs: T.Any) -> NSBundleModule:
    return NSBundleModule(*args, **kwargs)


class NSBundleModule(NewExtensionModule):
    INFO = ModuleInfo('nsbundle', '1.7.99')

    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.methods.update({
            'application': self.application,
            'framework': self.framework,
        })

    @FeatureNew('nsbundle.application', '1.7.99')
    @typed_pos_args('nsbundle.application', (str,), varargs=SOURCES_VARARGS)
    @typed_kwargs('nsbundle.application', *NSAPP_KWS, allow_unknown=True)
    def application(self, state: ModuleState, args: T.Tuple[str, SourcesVarargsType], kwargs: kwtypes.AppBundle
                    ) -> ModuleReturnValue:
        tgt = state.create_build_target(AppBundle, args, kwargs)
        return ModuleReturnValue(tgt, [tgt])

    @FeatureNew('nsbundle.framework', '1.7.99')
    @typed_pos_args('nsbundle.framework', (str,), varargs=SOURCES_VARARGS)
    @typed_kwargs('nsbundle.framework', *NSFRAMEWORK_KWS, allow_unknown=True)
    def framework(self, state: ModuleState, args: T.Tuple[str, SourcesVarargsType], kwargs: kwtypes.FrameworkBundle
                  ) -> ModuleReturnValue:
        tgt = state.create_build_target(FrameworkBundle, args, kwargs)
        return ModuleReturnValue(tgt, [tgt])
