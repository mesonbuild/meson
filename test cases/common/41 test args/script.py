#!/usr/bin/env python3

import os
import sys

assert os.path.isabs(sys.argv[1])
assert 'python' in os.path.basename(sys.argv[1])
exit(0)
