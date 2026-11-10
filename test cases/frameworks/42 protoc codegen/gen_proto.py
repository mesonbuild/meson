#!/usr/bin/env python3

# Writes a proto file for each output path. The message name is the file
# stem in CamelCase: multi_b.proto -> MultiB.

import os
import sys

for path in sys.argv[1:]:
    stem = os.path.splitext(os.path.basename(path))[0]
    name = ''.join(part.capitalize() for part in stem.split('_'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'syntax = "proto3";\n\nmessage {name} {{\n  string value = 1;\n}}\n')
