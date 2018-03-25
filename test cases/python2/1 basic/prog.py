#!/usr/bin/env python2

from gluon import gluonator
import sys

print('Running mainprog from root dir.')

if gluonator.gluoninate() != 42:
    sys.exit(1)
