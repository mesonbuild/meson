#!/usr/bin/env python3

import os
import sys

if len(sys.argv) == 2:
    assert(os.path.exists(sys.argv[1]))
elif len(sys.argv) == 3:
    f1 = open(sys.argv[1], 'rb').read()
    f2 = open(sys.argv[2], 'rb').read()
    if f1 != f2:
        raise RuntimeError('{!r} != {!r}'.format(f1, f2))
else:
    raise AssertionError
