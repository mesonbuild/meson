#! /usr/bin/env python3
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    for l in f:
        l = l.rstrip()
        print(l.replace(sys.argv[2], sys.argv[3]))
