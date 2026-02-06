# SPDX-License-Identifier: Apache-2.0
# Copyright 2022 The Meson development team

from __future__ import annotations
import typing as T

from .backends import Backend
from .. import mlog
from ..mesonlib import MesonBugException


class NoneBackend(Backend):

    name = 'none'

    def generate(self, capture: bool = False, vslite_ctx: T.Optional[T.Dict] = None) -> None:
        # Check for (currently) unexpected capture arg use cases -
        if capture:
            raise MesonBugException('We do not expect the none backend to generate with \'capture = True\'')
        if vslite_ctx:
            raise MesonBugException('We do not expect the none backend to be given a valid \'vslite_ctx\'')

        # The `meson convert` tool generates build targets, but uses the none backend
        # The below clause covers the non-convert use cases of the none backend, when
        # build targets are not generated.
        if not self.build.get_targets():
            mlog.log('Generating simple install-only backend')
            self.serialize_tests()
            self.create_install_data_files()
