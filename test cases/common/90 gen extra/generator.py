#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2024 Intel Corporation

from __future__ import annotations
import argparse
import os
import typing as T


def find_file(name: str, includes: T.List[str]) -> str:
    if os.path.exists(name):
        return name
    for i in includes:
        trial = os.path.join(i, name)
        if os.path.exists(trial):
            return trial
    raise RuntimeError('Did not find', name, 'in any of the include directories', ', '.join(includes))


def read_file(name: str, includes: T.List[str]) -> T.Iterable[str]:
    fname = find_file(name, includes)
    with open(fname, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            if line.startswith(':include::'):
                included = line.split('::', 1)[1].strip()
                yield from read_file(included, includes)
            else:
                yield line


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--include-dir', action='append', dest='includes')
    args = parser.parse_args()

    with open(args.output, 'w', encoding='utf-8') as f:
        for line in read_file(args.input, args.includes):
            f.write(line)


if __name__ == "__main__":
    main()
