#!/usr/bin/env python3

# NOTE: this file does not have the executable bit set. This tests that
# Meson can automatically parse shebang lines.

import sys

template = '#define RET_VAL %s\n'
output = template % (open(sys.argv[1]).readline().strip())
open(sys.argv[2], 'w').write(output)
