# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2017 The Meson development team
# Copyright © 2023-2025 Intel Corporation

"""Response file syntaxes and quoting."""

from __future__ import annotations

import enum
import re
import typing as T

from ..mesonlib import cmd_quote

@enum.unique
class RSPFileSyntax(enum.Enum):

    """Which RSP file syntax the compiler supports."""

    MSVC = enum.auto()
    GCC = enum.auto()
    TASKING = enum.auto()
    NASM = enum.auto()


GCC_RSP_UNSAFE_PAT = re.compile(r'[^\w@%+=:,./-]', re.ASCII)

def gcc_rsp_quote(s: str) -> str:
    # see: the function buildargv() in libiberty
    #
    # Up to GCC 15 (and in clang), a backslash *always* escapes the following
    # character, even inside single quotes.  Starting with GCC 16, backslashes
    # inside single quotes are literal as in sh.  Avoid quotes and escape
    # every special character with a backslash, which works the same way in
    # both cases.  The exception is newlines, for which a backslash is a line
    # continuation in sh; place them in single quotes instead.

    if not s:
        return "''"
    return GCC_RSP_UNSAFE_PAT.sub(lambda m: "'\n'" if m.group() == '\n' else '\\' + m.group(), s)

def rsp_file_flag(syntax: RSPFileSyntax) -> str:
    if syntax is RSPFileSyntax.NASM:
        return '-@'
    if syntax is RSPFileSyntax.TASKING:
        return '--option-file='
    return '@'

def rsp_quote_func(syntax: RSPFileSyntax) -> T.Callable[[str], str]:
    if syntax in {RSPFileSyntax.MSVC, RSPFileSyntax.TASKING}:
        return cmd_quote
    return gcc_rsp_quote
