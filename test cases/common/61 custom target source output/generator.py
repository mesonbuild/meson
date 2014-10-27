#!/usr/bin/env python3

import sys, os

if len(sys.argv) != 2:
    print(sys.argv[0], '<output dir>')

odir = sys.argv[1]

open(os.path.join(odir, 'mylib.h'), 'w').write('int func();\n')
open(os.path.join(odir, 'mylib.c'), 'w').write('''int func() {
    return 0;
}
''')
