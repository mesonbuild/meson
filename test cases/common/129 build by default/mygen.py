#!/usr/bin/env python3

import sys

ifile = open(sys.argv[1])
ofile = open(sys.argv[2], 'w', encoding='utf-8')

ofile.write(ifile.read())
