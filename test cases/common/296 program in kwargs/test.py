#!/usr/bin/env python3

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('sometool')
    parser.parse_args()


if __name__ == "__main__":
    main()
