#!/usr/bin/env python3

import sys, os

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(sys.argv[0], 'object', 'output')
        sys.exit(1)
    objExists = os.path.exists(sys.argv[1])
    with open(sys.argv[2], 'wb') as out:
        out.write(('pass' if objExists else 'fail').encode('UTF8'))
    sys.exit(0 if objExists else 1)
