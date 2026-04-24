#!/usr/bin/env python3
import sys

with open(sys.argv[1], 'r') as infile, \
     open(sys.argv[2], 'w', encoding='utf-8') as outfile:

    outfile.write(infile.read())
