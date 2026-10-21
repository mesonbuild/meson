#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson development team

import argparse
import subprocess
import sys
import difflib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('expected', help='the diff we expected')
    parser.add_argument('meson_cmd_path', nargs='+')
    args = parser.parse_args()

    result = subprocess.run([
        *args.meson_cmd_path,
        'format',
        '--recursive',
        '--check-diff',
        'recurse/meson.build',
    ], capture_output=True, text=True)

    actual = result.stdout.replace('\\', '/').splitlines(keepends=True)
    with open(args.expected, 'r', encoding='utf-8') as f:
        expected = f.readlines()

    if actual == expected:
        return 0

    diff = difflib.ndiff(expected, actual)
    for line in diff:
        print(line, file=sys.stderr, end='')
    return 1


if __name__ == "__main__":
    sys.exit(main())
