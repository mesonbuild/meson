#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

from __future__ import annotations
import argparse
import difflib
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('expected')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content == args.expected:
        for d in difflib.ndiff(content, args.expected):
            print(d, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
