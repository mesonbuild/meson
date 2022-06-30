#!/usr/bin/env python3

import argparse
import shutil


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    args = parser.parse_args()

    shutil.copyfile(args.input, args.output)


if __name__ == "__main__":
    main()
