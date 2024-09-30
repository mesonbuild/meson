#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

import argparse
import sys
import difflib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('actual', help='The transformed contents')
    parser.add_argument('expected', help='the contents we expected')
    args = parser.parse_args()

    with open(args.actual, 'r') as f:
        actual = f.readlines()
    with open(args.expected, 'r') as f:
        expected = f.readlines()

    if actual == expected:
        return 0

    diff = difflib.ndiff(expected, actual)
    for line in diff:
        print(line, file=sys.stderr, end='')
    return 1


if __name__ == "__main__":
    sys.exit(main())
