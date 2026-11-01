#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 The Meson development team

import sys
import subprocess

subprocess.run([sys.argv[1]] + sys.argv[3:], cwd=sys.argv[2])
