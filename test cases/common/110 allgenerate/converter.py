#!/usr/bin/env python3

import sys

ifile = sys.argv[1]
ofile = sys.argv[2]

open(ofile, 'w', encoding='utf-8').write(open(ifile).read())
