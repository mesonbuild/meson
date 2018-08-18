#!/usr/bin/env python3

from __future__ import print_function

import sys

if sys.argv[1] == 'correct':
    print('Argument is correct.')
    sys.exit(0)
print('Argument is incorrect:', sys.argv[1])
sys.exit(1)
