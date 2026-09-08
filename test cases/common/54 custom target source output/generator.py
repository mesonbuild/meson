#!/usr/bin/env python3

import sys
import os

if len(sys.argv) != 2:
    print(sys.argv[0], '<output dir>')

odir = sys.argv[1]

with open(os.path.join(odir, 'mylib.h'), 'w', encoding='utf-8') as f:
    f.write('int func(void);\n')
with open(os.path.join(odir, 'mylib.c'), 'w', encoding='utf-8') as f:
    f.write('''int func(void) {
    return 0;
}
''')
