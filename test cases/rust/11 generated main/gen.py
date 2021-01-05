#!/usr/bin/env python3

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    args = parser.parse_args()

    with open(args.out, 'w') as f:
        f.write('fn main() { println!("I prefer tarnish, actually.") }')


if __name__ == "__main__":
    main()
