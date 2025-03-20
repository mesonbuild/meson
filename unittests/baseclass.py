# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Intel Corporation

from __future__ import annotations

from unittest import TestCase, mock
import itertools
import os

from mesonbuild.compilers.compilers import CFLAGS_MAPPING

class BaseMesonTest(TestCase):

    """Base test class for all Meson tests that does basic environment setup."""

    env_patch: mock._patch_dict

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.env_patch = mock.patch.dict(os.environ)
        cls.env_patch.start()

        os.environ['COLUMNS'] = '80'
        os.environ['PYTHONIOENCODING'] = 'utf8'

        # Remove any CFlags, etc coming from an external environment so that we
        # get what we expect
        for flag in itertools.chain(['CPPFLAGS', 'LDFLAGS'], CFLAGS_MAPPING.values()):
            if flag in os.environ:
                del os.environ[flag]

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.env_patch.stop()
