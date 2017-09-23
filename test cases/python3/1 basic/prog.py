#!/usr/bin/env python3

import sys

from gluon import gluonator

print('Running mainprog from root dir.')

if gluonator.gluoninate() != 42:
    sys.exit(1)
