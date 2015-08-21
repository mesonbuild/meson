#!/usr/bin/env python3

import sys

if open(sys.argv[1]).read() != 'contents\n':
  sys.exit(1)
