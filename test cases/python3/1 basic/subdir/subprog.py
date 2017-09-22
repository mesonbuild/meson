#!/usr/bin/env python3

# In order to run this program, PYTHONPATH must be set to
# point to source root.

import sys

from gluon import gluonator

print('Running mainprog from subdir.')

if gluonator.gluoninate() != 42:
    sys.exit(1)
