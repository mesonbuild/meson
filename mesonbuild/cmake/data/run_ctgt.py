#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import sys

commands = [[]]
SEPERATOR = ';;;'

# Generate CMD parameters
parser = argparse.ArgumentParser(description='Wrapper for add_custom_command')
parser.add_argument('-d', '--directory', type=str, metavar='D', required=True, help='Working directory to cwd to')
parser.add_argument('-o', '--outputs', nargs='+', metavar='O', required=True, help='Expected output files')
parser.add_argument('-O', '--original-outputs', nargs='+', metavar='O', required=True, help='Output files expected by CMake')
parser.add_argument('commands', nargs=argparse.REMAINDER, help='A "{}" seperated list of commands'.format(SEPERATOR))

# Parse
args = parser.parse_args()

if len(args.outputs) != len(args.original_outputs):
    print('Length of output list and original output list differ')
    sys.exit(1)

for i in args.commands:
    if i == SEPERATOR:
        commands += [[]]
        continue

    commands[-1] += [i]

# Execute
for i in commands:
    # Skip empty lists
    if not i:
        continue

    subprocess.run(i, cwd=args.directory)

# Copy outputs
zipped_outputs = zip(args.outputs, args.original_outputs)
for expected, generated in zipped_outputs:
    do_copy = False
    if not os.path.exists(expected):
        if not os.path.exists(generated):
            print('Unable to find generated file. This can cause the build to fail:')
            print(generated)
            do_copy = False
        else:
            do_copy = True
    elif os.path.exists(generated):
        if os.path.getmtime(generated) > os.path.getmtime(expected):
            do_copy = True

    if do_copy:
        if os.path.exists(expected):
            os.remove(expected)
        shutil.copyfile(generated, expected)
