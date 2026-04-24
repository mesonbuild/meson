#!/usr/bin/env python3

import sys


def main():
    with open(sys.argv[1], 'w', encoding='utf-8') as out:
        out.write(sys.argv[2])
        out.write('\n')


if __name__ == '__main__':
    main()
