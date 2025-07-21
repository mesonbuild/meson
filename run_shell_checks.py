#!/usr/bin/env python3

# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 The Meson development team

import pathlib
import sys

# DO NOT ADD FILES IN THIS LIST!
# They are here because they got added
# in the past before this was properly checked.
# Instead you should consider removing things
# from this list by rewriting them to Python.
#
# The CI scripts probably need to remain shell
# scripts due to the way the CI systems work.

permitted_files = (
    'ci/ciimage/common.sh',
    'ci/intel-scripts/cache_exclude_windows.sh',
    'ci/ciimage/opensuse/install.sh',
    'ci/ciimage/ubuntu-rolling/install.sh',
    'ci/ciimage/ubuntu-rolling/test.sh',
    'ci/ciimage/cuda-cross/install.sh',
    'ci/ciimage/cuda/install.sh',
    'ci/ciimage/bionic/install.sh',
    'ci/ciimage/fedora/install.sh',
    'ci/ciimage/arch/install.sh',
    'ci/ciimage/gentoo/install.sh',
    'manual tests/4 standalone binaries/myapp.sh',
    'manual tests/4 standalone binaries/osx_bundler.sh',
    'manual tests/4 standalone binaries/linux_bundler.sh',
    'manual tests/4 standalone binaries/build_osx_package.sh',
    'manual tests/4 standalone binaries/build_linux_package.sh',
    'test cases/failing test/3 ambiguous/test_runner.sh',
    'test cases/common/190 install_mode/runscript.sh',
    'test cases/common/48 file grabber/grabber.sh',
    'test cases/common/12 data/runscript.sh',
    'test cases/common/33 run program/scripts/hello.sh',
    )


def check_bad_files(filename_glob):
    num_errors = 0
    for f in pathlib.Path('.').glob(f'**/{filename_glob}'):
        if str(f) not in permitted_files:
            print('Forbidden file type:', f)
            num_errors += 1
    return num_errors

def check_deletions():
    num_errors = 0
    for f in permitted_files:
        p = pathlib.Path(f)
        if not p.is_file():
            print('Exception list has a file that does not exist:', f)
            num_errors += 1
    return num_errors

def check_shell_usage():
    total_errors = 0
    total_errors += check_bad_files('Makefile')
    total_errors += check_bad_files('*.sh')
    total_errors += check_bad_files('*.awk')
    total_errors += check_deletions()
    return total_errors

if __name__ == '__main__':
    sys.exit(check_shell_usage())

