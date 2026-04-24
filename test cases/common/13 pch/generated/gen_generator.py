#!/usr/bin/env python3
import sys

with open(sys.argv[1]) as f:
    content = f.read()
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    f.write(content)
