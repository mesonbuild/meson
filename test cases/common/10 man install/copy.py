#!/usr/bin/env python3

import argparse
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output', nargs='+')
    args = parser.parse_args()

    for o in args.output:
        shutil.copyfile(args.input, o)


if __name__ == '__main__':
    main()
