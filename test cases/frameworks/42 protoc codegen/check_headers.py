#!/usr/bin/env python3

# Usage: check_headers.py STAMP COUNT HEADER...
# Checks that the headers exist and that there are COUNT of them.

import os
import sys

stamp, count, headers = sys.argv[1], int(sys.argv[2]), sys.argv[3:]

if len(headers) != count:
    sys.exit(f'expected {count} headers, got {len(headers)}: {headers}')
for h in headers:
    if not h.endswith('.pb.h') or not os.path.isfile(h):
        sys.exit(f'not a generated header: {h}')

with open(stamp, 'w', encoding='utf-8') as f:
    f.write('ok\n')
