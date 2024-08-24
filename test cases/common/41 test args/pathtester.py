#!/usr/bin/env python3

import sys, subprocess

if sys.platform == 'win32':
    cmd = ['xcopy', '/?']
else:
    cmd = ['env']

rc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
sys.exit(rc.returncode)
