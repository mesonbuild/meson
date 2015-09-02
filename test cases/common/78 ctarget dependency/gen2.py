#!/usr/bin/env python3

import sys, os
from glob import glob

files = glob(os.path.join(sys.argv[1], '*.tmp'))
assert(len(files) == 1)

open(sys.argv[2], 'w').write(open(files[0], 'r').read())
