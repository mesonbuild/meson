#!/usr/bin/env python

import sys

with open(sys.argv[1], 'rb') as ifile, open(sys.argv[2], 'wb') as ofile:
    ofile.write(ifile.read())
