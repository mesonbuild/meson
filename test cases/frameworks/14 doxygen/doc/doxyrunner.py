#!/usr/bin/env python3

import sys, os, subprocess, shutil
import pathlib

from argparse import ArgumentParser

parser = ArgumentParser(description='Helper tool to integrate Doxygen with Meson')

parser.add_argument('--out',
                    required=True, help='Directory where to write final output.')
parser.add_argument('--scratch',
                    required=True,
                    help='Directory to use for temporary files.')
parser.add_argument('--stamp', required=True,
                    help='Path to stamp file.')
parser.add_argument('--dep', required=True,
                    help='Path to dependency file.')

def run_doxygen(meson_opts, extra_args):
    # This simulates a program that does not support a -o argument
    # but instead writes its output to cwd with a path segment
    # we need to get rid of.
    #
    # You can tell Doxygen where to output its sources, but only
    # in Doxyfile, not via the command line.
    doxyfile = pathlib.Path(extra_args[0])
    outdir = pathlib.Path(meson_opts.out)
    scratchdir = pathlib.Path(meson_opts.scratch)
    if scratchdir.exists():
        shutil.rmtree(scratchdir)
    scratchdir.mkdir(parents=True)
    if outdir.exists():
        shutil.rmtree(outdir)
    shutil.copy(doxyfile, scratchdir)
    doxyrc = subprocess.call(['doxygen', doxyfile.name], cwd=scratchdir)
    docdir = scratchdir / 'doc'
    html = docdir / 'html'
    shutil.copytree(html, outdir / 'html')
    if doxyrc != 0:
        sys.exit(doxyrc)
    with open(meson_opts.dep, 'w') as depfile:
        depfile.write(f'"{meson_opts.stamp}": \n')
    # Always touch the stamp file last after every other step has succeeded.
    with open(meson_opts.stamp, 'w'):
        pass

if __name__ == '__main__':
    for i in range(len(sys.argv)):
        if sys.argv[i] == '--':
            run_doxygen(parser.parse_args(sys.argv[1:i]), sys.argv[i+1:])
            sys.exit(0)
    sys.exit('Mandatory separator argument "--" missing.')
