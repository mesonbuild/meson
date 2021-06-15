# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

from .base import DependencyTypeName, ExternalDependency, DependencyMethods
import typing as T

if T.TYPE_CHECKING:
    from ..environment import Environment

__all__ = [
    'SystemDependency',
]


class SystemDependency(ExternalDependency):

    """Dependency base for System type dependencies."""

    def __init__(self, name: str, env: 'Environment', kwargs: T.Dict[str, T.Any],
                 language: T.Optional[str] = None) -> None:
        super().__init__(DependencyTypeName('system'), env, kwargs, language=language)
        self.name = name

    @staticmethod
    def get_methods() -> T.List[DependencyMethods]:
        return [DependencyMethods.SYSTEM]

    def log_tried(self) -> str:
        return 'system'
