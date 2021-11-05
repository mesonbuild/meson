#!/usr/bin/env python3

from pathlib import Path
import sys

ifile = sys.argv[1]
ofile = sys.argv[2]


resname = Path(ifile).stem

templ = 'const char %s[] = "%s";\n'
with open(ofile, 'w') as f:
    f.write(templ % (resname, resname))
