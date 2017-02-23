#!/usr/bin/env python3

import sys

with open(sys.argv[1]) as f:
    if f.read() != 'contents\n':
        sys.exit(1)
