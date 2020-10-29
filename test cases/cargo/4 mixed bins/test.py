#!/usr/bin/env python3

import argparse
import subprocess
import sys

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('bin')
    parser.add_argument('expected')
    args = parser.parse_args()

    ret = subprocess.run(args.bin, stdout=subprocess.PIPE)
    out = ret.stdout.decode().strip()
    if out == args.expected:
        return 0
    print(f'Expected "{args.expected}", but got "{out}"')
    return 1


if  __name__ == "__main__":
    sys.exit(main())
