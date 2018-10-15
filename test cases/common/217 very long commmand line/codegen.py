#!/usr/bin/env python3

import sys

with open(sys.argv[2], 'w') as f:
    print('int func{n}() {{ return {n}; }}'.format(n=sys.argv[1]), file=f)
