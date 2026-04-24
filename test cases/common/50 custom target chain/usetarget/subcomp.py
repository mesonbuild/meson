#!/usr/bin/env python3

import sys

with open(sys.argv[1], 'rb') as ifile:
    with open(sys.argv[2], 'w', encoding='utf-8') as ofile:
        ofile.write('Everything ok.\n')
