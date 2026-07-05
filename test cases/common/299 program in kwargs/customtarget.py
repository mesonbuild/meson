#!/usr/bin/env python3

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('sometool')
    parser.add_argument('output')
    args = parser.parse_args()

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write('')


if __name__ == "__main__":
    main()
