#!/usr/bin/env python3

import subprocess
import sys

print('Wrapper called')
subprocess.check_call(['gcc'] + sys.argv[1:])
