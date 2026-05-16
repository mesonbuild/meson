#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Arthur Grillo

import argparse
import subprocess
import sys
import difflib


def compare(actual: str, expected: str) -> int:
    if actual == expected:
        return 0

    diff = difflib.ndiff(expected, actual)
    for line in diff:
        print(line, file=sys.stderr, end='')
    return 1

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('meson_cmd_path', nargs='+')

    args = parser.parse_args()

    result = subprocess.run([
        *args.meson_cmd_path,
        'format',
        '--recursive',
        '--subprojects',
        '--check-diff',
    ], capture_output=True, text=True)

    with open('subprojects/find-me/expected.diff', 'r', encoding='utf-8') as f:
        actual = result.stdout.replace('\\', '/')
        expected = f.read()

        return compare(
            actual,
            expected,
        )

if __name__ == "__main__":
    sys.exit(main())
