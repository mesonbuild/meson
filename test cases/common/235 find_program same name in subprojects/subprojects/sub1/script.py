#!/usr/bin/env python3
# SPDX-license-identifier: Apache-2.0

import argparse

def main() -> None:
    parser = argparse.ArgumentParser(prog='script.py')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    parser.parse_args()

    exit(0)


if __name__ == "__main__":
    main()
