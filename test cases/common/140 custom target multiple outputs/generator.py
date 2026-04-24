#!/usr/bin/env python3

import sys, os

if len(sys.argv) != 3:
    print(sys.argv[0], '<namespace>', '<output dir>')

name = sys.argv[1]
odir = sys.argv[2]

with open(os.path.join(odir, name + '.h'), 'w', encoding='utf-8') as f:
    f.write('int func();\n')
with open(os.path.join(odir, name + '.sh'), 'w', encoding='utf-8') as f:
    f.write('#!/bin/bash')
