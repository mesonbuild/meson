#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
from dataclasses import dataclass
import os
import typing as T

# This is a fast-path for users of convert/check-platforms. It provides a way of select power
# users to not have to type the long '--config=<PATH1> --dependencies=<PATH2> --platforms=<PATH3>'
# file name. There is a certain bit of hardcoding, but given this tool is for intended for a
# small number of power users (Mesa, QEMU, ..) that should be fine.
#
# The fast path is based on "hermetic" and "git_project" key tuple. That is used to lookup
# a particular directory.  The fastpath is opinionated: the TOML files should be:
#
#  <git_project>.toml
#  dependencies.toml
#  platforms.toml
#
# These files are all in one, subdirectory in the target git project.
#
# Non-power users will have type it the long way or create one-off shell scripts for the
# purpose. Power users can just submit patches upstream.


@dataclass(frozen=True)
class HermeticFastPathKey:
    hermetic_project: str
    git_project: str


HERMETIC_FAST_MAP: T.Dict[HermeticFastPathKey, str] = {
    HermeticFastPathKey('android', 'aosp_mesa3d'): 'src/gfxstream/hermetic/android',
    HermeticFastPathKey('android', 'rutabaga_gfx'): 'build',
    HermeticFastPathKey('fuchsia', 'mesa3d'): 'src/gfxstream/hermetic/fuchsia',
    HermeticFastPathKey('test', 'basic_soong'): 'hermetic_files',
    HermeticFastPathKey('test', 'basic_bazel'): 'hermetic_files',
}


def get_known_toml_files(hermetic_project: str, git_project: str,
                         project_dir: str) -> T.Optional[T.Tuple[str, str, str]]:  # fmt: skip
    key = HermeticFastPathKey(hermetic_project, git_project)
    directory = HERMETIC_FAST_MAP.get(key)

    if directory is None:
        return None

    base_path = os.path.join(project_dir, directory)
    config_path = os.path.join(base_path, f'{git_project}.toml')
    platforms_path = os.path.join(base_path, 'platforms.toml')
    dependencies_path = os.path.join(base_path, 'dependencies.toml')
    return config_path, platforms_path, dependencies_path
