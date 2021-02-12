#!/usr/bin/env python3
# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('bin')
    parser.add_argument('expected')
    args = parser.parse_args()

    out = subprocess.run(args.bin, stdout=subprocess.PIPE)
    if out.returncode != 0:
        exit(1)

    actual = out.stdout.decode().rstrip()
    if actual != args.expected:
        print('got: ', actual, file=sys.stderr)
        print('exepcted: ', args.expected, file=sys.stderr)
        exit(1)
    exit(0)

if __name__ == '__main__':
    main()
