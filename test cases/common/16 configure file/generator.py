#!/usr/bin/env python3

import sys

if len(sys.argv) != 3:
    print("Wrong amount of parameters.")

# Just test that it exists.
with open(sys.argv[1], 'r') as ifile:
    pass

with open(sys.argv[2], 'w') as ofile:
    ofile.write("#define ZERO_RESULT 0\n")
