#!/usr/bin/env python3

import sys

f = open(sys.argv[1], 'w', encoding='utf-8')
f.write('#define RETURN_VALUE 0')
f.close()
