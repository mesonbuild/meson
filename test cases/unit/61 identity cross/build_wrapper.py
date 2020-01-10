#!/usr/bin/env python3

import subprocess, sys

subprocess.call(["cc", "-DEXTERNAL_BUILD"] + sys.argv[1:])
