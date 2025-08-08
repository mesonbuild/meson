# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Red Hat, Inc

import glob, os, pathlib, shutil, subprocess, sys, unittest

from run_tests import (
    Backend
)

from .allplatformstests import git_init
from .baseplatformtests import BasePlatformTests
from .helpers import *

from mesonbuild.mesonlib import MachineChoice, TemporaryDirectoryWinProof, is_windows
from mesonbuild.modules.selinux import parse_makefile_variables

class SELinuxTests(BasePlatformTests):
    def test_parse_makefile_variables(self):
        makefile_content = f"""
# Makefile variables
TYPE ?= mcs
NAME ?= targeted
DISTRO ?= redhat
MONOLITHIC ?= n
DIRECT_INITRC ?= n

# This is a target, not a variable, and should be ignored by the parser
all:
\techo "Building..."

# Override directives
override UBAC := n
override MLS_SENS := 16
override MLS_CATS := 1024
override MCS_CATS := 1024

# This conditional assignment should be ignored because TYPE is already set.
TYPE ?= this_will_be_ignored
"""
        variables = parse_makefile_variables(makefile_content)
        self.assertEqual(variables, {
            'TYPE': 'mcs',
            'NAME': 'targeted',
            'DISTRO': 'redhat',
            'MONOLITHIC': 'n',
            'DIRECT_INITRC': 'n',
            'UBAC': 'n',
            'MLS_SENS': '16',
            'MLS_CATS': '1024',
            'MCS_CATS': '1024'
        })

    def test_parse_makefile_variables_with_empty_content(self):
        makefile_content = ""
        variables = parse_makefile_variables(makefile_content, {})
        self.assertEqual(variables, {})
