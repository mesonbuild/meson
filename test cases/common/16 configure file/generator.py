#!/usr/bin/env python

# On some platforms "python" points to Python 2
# on others to Python 3. Work with both.

from __future__ import print_function
import sys, os

if len(sys.argv) != 3:
    print("Wrong amount of parameters.")

assert(os.path.exists(sys.argv[1]))

with open(sys.argv[2], 'w') as ofile:
    ofile.write("#define ZERO_RESULT 0\n")
