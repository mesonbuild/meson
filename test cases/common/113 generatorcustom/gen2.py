#!/usr/bin/env python3

import os
import sys

with open(sys.argv[1], 'w') as f:
    var = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    f.write('const char {0}[] = "{0}";'.format(var))
