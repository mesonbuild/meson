#!/usr/bin/env python3

import sys, os

if len(sys.argv) != 3:
    print("You is fail.")
    sys.exit(1)

with open(sys.argv[1]) as f:
    val = f.read().strip()
outdir = sys.argv[2]

outsrc = os.path.join(outdir, 'source.json')

with open(outsrc, 'w') as f:
    for line in val.split('\n'):
        if not line.startswith('#'):
            f.write('{}\n'.format(line))
