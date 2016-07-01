#!/usr/bin/env python3

import sys

open(sys.argv[2], 'wb').write(open(sys.argv[1], 'rb').read())
