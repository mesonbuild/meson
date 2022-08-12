#!/usr/bin/env python3
# SPDX-license-identifier: Apache-2.0

import argparse
import sys

EXPECTED = '"1.0.0" "X Version 11"\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        data = f.read()

    if data == EXPECTED:
        return 0
    print(f'expected: {EXPECTED}', file=sys.stderr)
    print(f'actual:   {data}', file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
