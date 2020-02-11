#!/usr/bin/env python3

import os
import sys

if len(sys.argv) == 2:
    assert(os.path.exists(sys.argv[1]))
elif len(sys.argv) == 3:
    f1 = sys.argv[1]
    f2 = sys.argv[2]
    m1 = os.stat(f1).st_mtime_ns
    m2 = os.stat(f2).st_mtime_ns
    # Compare only os.stat()
    if m1 != m2:
        raise RuntimeError('mtime of {!r} () != mtime of {!r} ()'.format(f1, m1, f2, m2))
    import filecmp
    if not filecmp.cmp(f1, f2):
        raise RuntimeError('{!r} != {!r}'.format(f1, f2))
else:
    raise AssertionError
