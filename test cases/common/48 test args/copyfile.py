#!/usr/bin/env python3

import sys
import shutil

# If either of these use `\` as the path separator, it will cause problems with
# MSYS, MSYS2, and Cygwin tools that expect the path separator to always be
# `/`. All Native-Windows tools also accept `/` as the path separator, so
# it's fine to always use that for arguments.
# See: https://github.com/mesonbuild/meson/issues/1564
#
# Note that this applies to both MinGW and MSVC toolchains since people use
# MSYS tools with both, or use a mixed toolchain environment.
if '\\' in sys.argv[1]:
    raise RuntimeError('Found \\ in source arg {!r}'.format(sys.argv[1]))

if '\\' in sys.argv[2]:
    raise RuntimeError('Found \\ in dest arg {!r}'.format(sys.argv[2]))

shutil.copyfile(sys.argv[1], sys.argv[2])
