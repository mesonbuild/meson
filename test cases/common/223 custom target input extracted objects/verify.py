#!/usr/bin/env python3

import sys

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(sys.argv[0], 'output')
        sys.exit(1)
    with open(sys.argv[1], 'rb') as resultFile:
        result = resultFile.read().decode('UTF8')
    sys.exit(0 if result == 'pass' else 1)
