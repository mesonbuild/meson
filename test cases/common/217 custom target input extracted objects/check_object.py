#!/usr/bin/env python3

import sys, os

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(sys.argv[0], 'object', 'output')
        sys.exit(1)
    elif os.path.exists(sys.argv[1]):
        with open(sys.argv[2], 'wb') as out:
            pass
    else:
        sys.exit(1)
