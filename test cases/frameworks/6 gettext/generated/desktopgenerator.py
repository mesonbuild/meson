#!/usr/bin/env python3

import sys, shutil

ifile = sys.argv[1]
ofile = sys.argv[2]

os.unlink(ofile)
shutil.copy(ifile, ofile)
