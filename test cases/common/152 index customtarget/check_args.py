#!python3

import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print(sys.argv)
        return 1
    # vs backend gives abs path
    if os.path.basename(sys.argv[2]) != 'gen.c':
        print(sys.argv)
        return 2
    Path(sys.argv[1]).touch()

    return 0

if __name__ == '__main__':
    sys.exit(main())
