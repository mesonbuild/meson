#!/usr/bin/env python3

# Any exception causes return value to be not zero, which is sufficient.

import sys

fc = open('/etc/apt/sources.list').read()
if 'artful' not in fc:
    sys.exit(1)
