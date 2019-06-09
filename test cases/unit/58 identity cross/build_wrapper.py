#!/usr/bin/env python

import subprocess, sys

subprocess.call(["cc", "-DEXTERNAL_BUILD"] + sys.argv[1:])
