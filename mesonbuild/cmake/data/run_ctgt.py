#!/usr/bin/env python3

import argparse
import subprocess
import shutil
import os
import sys

commands = [[]]
SEPARATOR = ';;;'

# Generate CMD parameters
parser = argparse.ArgumentParser(description='Wrapper for add_custom_command')
parser.add_argument('-d', '--directory', type=str, metavar='D', required=True, help='Working directory to cwd to')
parser.add_argument('-o', '--outputs', nargs='+', metavar='O', required=True, help='Expected output files')
parser.add_argument('-O', '--original-outputs', nargs='*', metavar='O', default=[], help='Output files expected by CMake')
parser.add_argument('commands', nargs=argparse.REMAINDER, help='A "{}" seperated list of commands'.format(SEPARATOR))

# Parse
args = parser.parse_args()

dummy_target = None
if len(args.outputs) == 1 and len(args.original_outputs) == 0:
    dummy_target = args.outputs[0]
elif len(args.outputs) != len(args.original_outputs):
    print('Length of output list and original output list differ')
    sys.exit(1)

for i in args.commands:
    if i == SEPARATOR:
        commands += [[]]
        continue

    i = i.replace('"', '')  # Remove lefover quotes
    commands[-1] += [i]

# Execute
for i in commands:
    # Skip empty lists
    if not i:
        continue

    try:
        os.makedirs(args.directory, exist_ok=True)
        subprocess.run(i, cwd=args.directory, check=True)
    except subprocess.CalledProcessError:
        exit(1)

if dummy_target:
    with open(dummy_target, 'a'):
        os.utime(dummy_target, None)
    exit(0)

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
