#!/usr/bin/env python3

import sys

if len(sys.argv) != 3:
    print("Wrong amount of parameters.")

# Just test that it exists.
ifile = open(sys.argv[1], 'r')

ofile = open(sys.argv[2], 'w')
ofile.write("#define ZERO_RESULT 0\n")
ofile.close()
