#!/usr/bin/env python3

import os, sys, subprocess, argparse, pathlib

parser = argparse.ArgumentParser()

parser.add_argument('--private-dir', required=True)
parser.add_argument('-o', required=True)
parser.add_argument('cmparr', nargs='+')

static_linker = 'ar'

contents = '''#include<stdio.h>

void flob() {
    printf("Now flobbing.\\n");
}
'''

def generate_lib(outfile, private_dir, compiler_array):
    outdir = pathlib.Path(private_dir)
    if not outdir.exists():
        outdir.mkdir()
    c_file = outdir / 'flob.c'
    c_file.write_text(contents)
    o_file = c_file.with_suffix('.o')
    compile_cmd = compiler_array + ['-c', '-g', '-O2', '-o', o_file, c_file]
    subprocess.check_call(compile_cmd)
    out_file = pathlib.Path(outfile)
    if out_file.exists():
        out_file.unlink()
    link_cmd = [static_linker, 'csrD', outfile, o_file]
    subprocess.check_call(link_cmd)

if __name__ == '__main__':
    options = parser.parse_args()
    generate_lib(options.o, options.private_dir, options.cmparr)
    sys.exit(1)
