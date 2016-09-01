#!/usr/bin/env python3

import sys, os

output = sys.argv[-1]
inputs = sys.argv[1:-1]

with open(output, 'w') as ofile:
    ofile.write('#pragma once\n')
    for i in inputs:
        with open(i, 'r') as ifile:
            content = ifile.read()
        ofile.write(content)
        ofile.write('\n')
