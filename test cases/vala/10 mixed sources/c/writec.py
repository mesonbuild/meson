#!/usr/bin/env python3

import sys

c = '''int
retval(void) {
  return 0;
}
'''

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(c)
