#!/usr/bin/env python3

import os
import sys

assert len(sys.argv) >= 3

fname = sys.argv[1]
check_strs = sys.argv[2:]

assert os.path.isfile(fname)
with open(fname, 'r', encoding='utf-8') as f:
    content = f.read()

for check_str in check_strs:
    assert check_str in content, f'{check_str!r} not found in {fname}'
