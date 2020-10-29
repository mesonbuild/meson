#!/usr/bin/env python3

import argparse
import subprocess
import sys

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('bin')
    args = parser.parse_args()

    ret = subprocess.run(args.bin, stdout=subprocess.PIPE)
    if ret.stdout == b'Hello World!\n':
        return 0
    print(f'Expected "Hello World!\n", but got "{ret.stdout.decode()}"')
    return 1


if  __name__ == "__main__":
    sys.exit(main())
