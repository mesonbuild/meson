#!/usr/bin/env python3

import sys, os

template = '''#pragma once

#define THE_NUMBER {}
'''

data = open(os.path.join(sys.argv[1], 'raw.dat')).readline().strip()
open(os.path.join(sys.argv[2], 'generated.h'), 'w').write(template.format(data))
