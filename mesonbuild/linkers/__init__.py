# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2021 The Meson development team

from .base import ArLikeLinker
from .detect import (
    defaults,
    guess_win_linker,
    guess_nix_linker,
)
from .linkers import VisualStudioLikeLinkerMixin, StaticLinker

__all__ = [
    # base.py
    'ArLikeLinker',

    # detect.py
    'defaults',
    'guess_win_linker',
    'guess_nix_linker',

    # linkers.py
    'StaticLinker',
    'VisualStudioLikeLinkerMixin',
]
