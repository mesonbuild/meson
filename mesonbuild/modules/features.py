# SPDX-License-Identifier: Apache-2.0
# Copyright © 2023 Intel Corporation

from __future__ import annotations

import typing as T

from . import ExtensionModule, ModuleReturnValue, ModuleInfo
from ..coredata import UserFeatureOption
from ..interpreter.type_checking import in_set_validator
from ..interpreterbase import InvalidArguments, KwargInfo, typed_kwargs, typed_pos_args, noKwargs, TYPE_kwargs

if T.TYPE_CHECKING:
    from typing_extensions import Literal, TypedDict

    from ..interpreter import Interpreter
    from . import ModuleState

    PRED_MODE = Literal['auto', 'enabled', 'disabled', 'allowed', 'denied']

    class AnyKWArgs(TypedDict):

        mode: PRED_MODE


_PRED_MODE_KW = KwargInfo(
    'mode', str, default='allowed',
    validator=in_set_validator({'auto', 'enabled', 'disabled', 'allowed', 'denied'}),
)


class FeatureModule(ExtensionModule):

    """Helper functions for working with Features"""

    INFO = ModuleInfo('features', '1.2.0', unstable=True)

    def __init__(self, interpreter: Interpreter) -> None:
        super().__init__(interpreter)
        self.methods.update({
            'new': self.new,
        })

    @typed_pos_args('feature.new', str, str)
    @noKwargs
    def new(self, state: ModuleState, args: T.Tuple[str, str], kwargs: TYPE_kwargs) -> ModuleReturnValue:
        """Create a new UserFeatureOption with the given name and initial value."""
        name, value = args
        if value not in {'auto', 'enabled', 'disabled'}:
            raise InvalidArguments('feature.new: second argument must be one of: "auto", "enabled", "disabled". Not', value)

        feat = UserFeatureOption('', value, False, name=name)

        return ModuleReturnValue(feat, [])

    @staticmethod
    def _get_pred_func(mode: PRED_MODE) -> T.Callable[[UserFeatureOption], bool]:
        """Get a preddicate testing function for the all and any methods.

        :param mode: The mode to test for
        :return: A callable which returns true when the predicate matches, otherwise false
        """
        if mode == 'auto':
            return lambda x: x.is_auto()
        elif mode == 'enabled':
            return lambda x: x.is_enabled()
        elif mode == 'disabled':
            return lambda x: x.is_disabled()
        elif mode == 'allowed':
            return lambda x: not x.is_disabled()
        return lambda x: not x.is_enabled()

    @typed_pos_args('feature.any', varargs=UserFeatureOption, min_varargs=1)
    @typed_kwargs('feature.all', _PRED_MODE_KW)
    def any(self, state: ModuleState,
            args: T.Tuple[T.List[UserFeatureOption]],
            kwargs: AnyKWArgs) -> bool:
        """Decide if any of the feature options are of the given value.

        value may be one of:
            enabled -- a value is enabled
            disabled -- a value is disabled
            auto -- a value is auto
            allowed -- a value is not disabled
            denied -- a value is not enabled

        For example:
            opt = feature.new('opt', 'auto') \\
                .disable_auto_if(
                    feature.any(EnabledOption, DisabledOption, value : 'auto'))
        """
        pred = self._get_pred_func(kwargs['mode'])
        return any(pred(x) for x in args[0])

    @typed_pos_args('feature.all', varargs=UserFeatureOption, min_varargs=1)
    @typed_kwargs('feature.all', _PRED_MODE_KW)
    def all(self, state: ModuleState,
            args: T.Tuple[T.List[UserFeatureOption]],
            kwargs: AnyKWArgs) -> bool:
        """Decide if all of the feature options are of the given value.

        value may be one of:
            enabled -- a value is enabled
            disabled -- a value is disabled
            auto -- a value is auto
            allowed -- a value is not disabled
            denied -- a value is not enabled

        For example:
            opt = feature.new('opt', 'auto') \\
                .disable_auto_if(
                    feature.all(EnabledOption, DisabledOption, value : 'auto'))
        """
        pred = self._get_pred_func(kwargs['mode'])
        return all(pred(x) for x in args[0])


def initialize(interp: Interpreter) -> FeatureModule:
    return FeatureModule(interp)
