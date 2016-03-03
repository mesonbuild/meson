#!/usr/bin/env python3

import sys, os

template = '''#pragma once

#define THE_NUMBER {}
#define THE_ARG1 {}
#define THE_ARG2 {}
'''

data = open(os.path.join(os.environ['MESON_SOURCE_ROOT'], 'raw.dat')).readline().strip()
open(os.path.join(os.environ['MESON_BUILD_ROOT'], 'generated.h'), 'w').write(template.format(data, sys.argv[1], sys.argv[2]))
