#!/usr/bin/env python3

import subprocess, sys

subprocess.call(["cc", "-DEXTERNAL_HOST"] + sys.argv[1:])
