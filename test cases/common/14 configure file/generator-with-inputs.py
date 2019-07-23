#!/usr/bin/env python3

import sys, os
from pathlib import Path

if len(sys.argv) != 4:
    print("Wrong amount of parameters.")
    exit(1)

build_dir = Path(os.environ['MESON_BUILD_ROOT'])
subdir = Path(os.environ['MESON_SUBDIR'])
inputf = [Path(x) for x in sys.argv[1:-1]]
outputf = Path(sys.argv[-1])

for i in inputf:
    assert(i.exists())

with outputf.open('w') as ofile:
    ofile.write("#define ZERO_RESULT 0\n")
