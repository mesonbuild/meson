#!/usr/bin/env python3

import sys, os

if len(sys.argv) != 3:
    print("You is fail.")
    sys.exit(1)

with open(sys.argv[1]) as f:
    val = f.read().strip()
outdir = sys.argv[2]

outhdr = os.path.join(outdir, 'source{}.h'.format(val))
outsrc = os.path.join(outdir, 'source{}.cpp'.format(val))

with open(outhdr, 'w', encoding='utf-8') as f:
    f.write('int func{}();\n'.format(val))
with open(outsrc, 'w', encoding='utf-8') as f:
    f.write('''int func{}() {{
    return 0;
}}
'''.format(val))
