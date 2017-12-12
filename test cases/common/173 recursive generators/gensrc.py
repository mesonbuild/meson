#!/usr/bin/env python3

import sys, os
import json

if len(sys.argv) != 3:
    print("You is fail.")
    sys.exit(1)

with open(sys.argv[1]) as f:
    val = json.loads(f.read().strip())
outdir = sys.argv[2]

outsrc = os.path.join(outdir, 'source.cpp')

with open(outsrc, 'w') as f:
    f.write(val['main'])
