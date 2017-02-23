#!/usr/bin/env python3

import os

template = '''#pragma once

#define THE_NUMBER {}
'''

input_file = os.path.join(os.environ['MESON_SOURCE_ROOT'], 'raw.dat')
output_file = os.path.join(os.environ['MESON_BUILD_ROOT'], 'generated.h')

with open(input_file) as f:
    data = f.readline().strip()
with open(output_file, 'w') as f:
    f.write(template.format(data))
