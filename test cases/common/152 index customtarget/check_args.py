#!python3

import sys
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print(sys.argv)
        return 1

    output, expected, *args = sys.argv[1:]
    actual = ','.join(args)
    if actual != expected:
        print('expected:', expected)
        print('actual:', actual)
        return 1

    Path(output).touch()

    return 0

if __name__ == '__main__':
    sys.exit(main())
