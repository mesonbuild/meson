#!/usr/bin/env python3

import sys, os

with open(sys.argv[1], 'rb') as ifile:
    open(sys.argv[2], 'w').write('Everything ok.\n')

