#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

from __future__ import annotations
import os
import typing as T

# This is a fast-path for users of convert/check-platforms. It provides a way of select power
# users to not have to type the long '--config=<PATH1> --dependencies=<PATH2> --platforms=<PATH3>'
# file name.
#
# The fast path is based on "hermetic" and "git_project" key tuple. That is used to lookup
# a particular directory in a Meson project standardized "hermetic" subdir.  The fastpath is
# opinionated: the TOML files should be:
#
#  <git_project>.toml
#  dependencies.toml
#  platforms.toml
#
# Non-power users will have type it the long way or create one-off shell scripts for the
# purpose. Power users can just submit patches upstream.

def get_known_toml_files(hermetic_project: str, git_project: str,
                         project_dir: str) -> T.Optional[T.Tuple[str, str, str]]:  # fmt: skip
    directory = 'hermetic/' + hermetic_project
    base_path = os.path.join(project_dir, directory)
    config_path = os.path.join(base_path, f'{git_project}.toml')
    platforms_path = os.path.join(base_path, 'platforms.toml')
    dependencies_path = os.path.join(base_path, 'dependencies.toml')
    return config_path, platforms_path, dependencies_path
