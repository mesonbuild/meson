#!/usr/bin/env python3

import sys
from glob import glob

files = glob('*.tmp')
assert(len(files) == 1)

open(sys.argv[1], 'w').write(open(files[0], 'r').read())
