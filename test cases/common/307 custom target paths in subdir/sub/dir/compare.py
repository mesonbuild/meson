#!/usr/bin/env python3

import sys

with open(sys.argv[1], encoding='utf-8') as a, open(sys.argv[2], encoding='utf-8') as b:
    if a.read() != b.read():
        sys.exit(f'{sys.argv[1]} and {sys.argv[2]} differ')

with open(sys.argv[3], 'w', encoding='utf-8') as f:
    f.write('ok\n')
