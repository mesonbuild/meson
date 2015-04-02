#!/usr/bin/env python3

import time, sys

# Make sure other script runs first if dependency
# is missing.
time.sleep(0.5)

contents = open(sys.argv[1], 'r').read()
open(sys.argv[2], 'w').write(contents)
