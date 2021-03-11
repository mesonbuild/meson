#!/usr/bin/env python3

import argparse
import subprocess
import sys

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('first')
    parser.add_argument('second')
    args = parser.parse_args()

    first = subprocess.run(args.first, stdout=subprocess.PIPE)
    second = subprocess.run(args.second, stdout=subprocess.PIPE)

    if first.stdout.strip() != second.stdout.strip():
        print("Values did not match!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()