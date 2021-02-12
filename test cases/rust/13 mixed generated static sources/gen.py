#!/usr/bin/env python3
# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    args = parser.parse_args()

    with open(args.output, 'w') as f:
        f.write('pub fn libfun() { println!("I prefer tarnish, actually.") }')


if __name__ == '__main__':
    main()
