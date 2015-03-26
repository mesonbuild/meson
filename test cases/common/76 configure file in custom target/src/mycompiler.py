#!/usr/bin/env python3

import sys

ifile = open(sys.argv[1])
if ifile.readline().strip() != '42':
    print('Incorrect input')
open(sys.argv[2], 'w').write('Success\n')
