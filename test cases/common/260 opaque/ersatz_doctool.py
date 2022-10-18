#!/usr/bin/env python3

import sys, os, subprocess, shutil
import pathlib

from argparse import ArgumentParser

# Argparse does not permit ignoring unknown args.
# Do it by hand.

known_args = ['--out',
              '--scratch',
              '--stamp',
              '--dep']

def is_known(arg):
    for a in known_args:
        if arg.startswith(a):
            return True
    return False

parser = ArgumentParser(description='Helper tool to test opaque generation')

parser.add_argument('--out',
                    required=True, help='Directory where to write final output.')
parser.add_argument('--scratch',
                    required=True,
                    help='Directory to use for temporary files.')
parser.add_argument('--stamp', required=True,
                    help='Path to stamp file.')
parser.add_argument('--dep', required=True,
                    help='Path to dependency file.')

def run_doxygen(meson_args, extra_args):
    if len(extra_args) != 1:
        sys.exit('Incorrect number of input arguments.')
    if extra_args[0] != '--foobar':
        sys.exit(f'Input arg is incorrect: {extra_args[0]}')
    known_args = [x for x in meson_args if is_known(x)]
    meson_opts = parser.parse_args(known_args)
    outdir = pathlib.Path(meson_opts.out)
    outsub = outdir / 'subdir'
    scratchdir = pathlib.Path(meson_opts.scratch)
    if os.path.exists(meson_opts.stamp):
        os.unlink(meson_opts.stamp)
    if not scratchdir.is_dir():
        sys.exit('Meson did not create scratch dir.')
    if not outdir.is_dir():
        sys.exit('Meson did not create out dir.')
    with open(scratchdir / 'dummy_file', 'wb'):
        pass
    with open(outdir / 'out_top.txt', 'wb'):
        pass
    outsub.mkdir(exist_ok=True)
    with open(outsub / 'out_subdir.txt', 'wb'):
        pass
    # Always touch the stamp file last after every other step has succeeded.
    with open(meson_opts.stamp, 'w'):
        pass

if __name__ == '__main__':
    for i in range(len(sys.argv)):
        if sys.argv[i] == '--':
            run_doxygen(sys.argv[1:i], sys.argv[i+1:])
            sys.exit(0)
    sys.exit('Mandatory separator argument "--" missing.')
