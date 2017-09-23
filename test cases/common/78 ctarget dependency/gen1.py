#!/usr/bin/env python3

import sys
import time

# Make sure other script runs first if dependency
# is missing.
time.sleep(0.5)

with open(sys.argv[1], 'r') as f:
    contents = f.read()
with open(sys.argv[2], 'w') as f:
    f.write(contents)
