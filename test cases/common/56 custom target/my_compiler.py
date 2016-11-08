#!/usr/bin/env python3

import sys

if __name__ == '__main__':
    if len(sys.argv) != 3 or not sys.argv[1].startswith('--input') or \
       not sys.argv[2].startswith('--output'):
        print(sys.argv[0], '--input=input_file --output=output_file')
        sys.exit(1)
    with open(sys.argv[1].split('=')[1]) as f:
        ifile = f.read()
    if ifile != 'This is a text only input file.\n':
        print('Malformed input')
        sys.exit(1)
    with open(sys.argv[2].split('=')[1], 'w') as ofile:
        ofile.write('This is a binary output file.\n')
