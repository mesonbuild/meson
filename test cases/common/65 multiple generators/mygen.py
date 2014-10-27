#!/usr/bin/env python3

import sys, os

if len(sys.argv) != 3:
    print("You is fail.")
    sys.exit(1)

val = open(sys.argv[1]).read().strip()
outdir = sys.argv[2]

outhdr = os.path.join(outdir, 'source%s.h' % val)
outsrc = os.path.join(outdir, 'source%s.cpp' % val)

open(outhdr, 'w').write('int func%s();\n' % val)
open(outsrc, 'w').write('''int func%s() {
    return 0;
}
''' % val)
