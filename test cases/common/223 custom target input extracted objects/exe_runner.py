#!/usr/bin/env python3

import sys, os

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(sys.argv[0], 'executable')
        sys.exit(1)
    program = sys.argv[1]
    os.execv(program, [program])
