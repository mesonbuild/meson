#!/usr/bin/env python3

import sys

ofile = sys.argv[1]
num = sys.argv[2]

with open(ofile, 'w', encoding='utf-8') as f:
    f.write(f'res{num}\n')
