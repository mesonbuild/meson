#!/usr/bin/env python

import subprocess, sys

subprocess.call(["cc", "-DEXTERNAL_HOST"] + sys.argv[1:])
