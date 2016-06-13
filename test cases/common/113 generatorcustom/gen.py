#!/usr/bin/env python3

import sys, os

ifile = sys.argv[1]
ofile = sys.argv[2]

resname = open(ifile, 'r').readline().strip()

templ = 'const char %s[] = "%s";\n'
open(ofile, 'w').write(templ % (resname, resname))
