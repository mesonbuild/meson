#!/usr/bin/env python3

import os
import sys

if sys.argv[1] not in os.environ:
    exit(42)
