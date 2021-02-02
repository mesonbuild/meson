# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

import argparse
import shutil


def iter_two(seq):
    itr = iter(seq)
    while True:
        try:
            yield next(itr), next(itr)
        except StopIteration:
            break


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('values', nargs="*")
    args = parser.parse_args()

    for i, o in iter_two(args.values):
        shutil.copyfile(i, o)


if __name__ == "__main__":
    main()
