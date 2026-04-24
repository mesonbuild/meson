#!/usr/bin/env python3
import sys

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    print('# this file does nothing', file=f)

with open(sys.argv[2], 'w', encoding='utf-8') as f:
    print('# this file does nothing', file=f)
