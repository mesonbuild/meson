#!/usr/bin/env python3

# Generates a static library, object file, source
# file and a header file.

import sys, os
import shutil, subprocess

funcname = open(sys.argv[1]).readline().strip()
outdir = sys.argv[2]

if not os.path.isdir(outdir):
    print('Outdir does not exist.')
    sys.exit(1)

if shutil.which('cl'):
    libsuffix = '.lib'
    is_vs = True
    compiler = 'cl'
    linker = 'lib'
else:
    libsuffix = '.a'
    is_vs = False
    linker = 'ar'
    compiler = shutil.which('gcc')
    if compiler is None:
        compiler = shutil.which('clang')
    if compiler is None:
        compiler = shutil.which('cc')
    if compiler is None:
        print('No known compilers found.')
        sys.exit(1)

objsuffix = '.o'

outo = os.path.join(outdir, funcname + objsuffix)
outa = os.path.join(outdir, funcname + libsuffix)
outh = os.path.join(outdir, funcname + '.h')
outc = os.path.join(outdir, funcname + '.c')

tmpc = 'diibadaaba.c'
tmpo = 'diibadaaba' + objsuffix

open(outc, 'w').write('''#include"%s.h"
int %s_in_src() {
  return 0;
}
''' % (funcname, funcname))

open(outh, 'w').write('''#pragma once
int %s_in_lib();
int %s_in_obj();
int %s_in_src();
''' % (funcname, funcname, funcname))

open(tmpc, 'w').write('''int %s_in_obj() {
  return 0;
}
''' % funcname)

if is_vs:
    subprocess.check_call([compiler, '/nologo', '/c', '/Fo' + outo, tmpc])
else:
    subprocess.check_call([compiler, '-c', '-o', outo, tmpc])

open(tmpc, 'w').write('''int %s_in_lib() {
  return 0;
}
''' % funcname)

if is_vs:
    subprocess.check_call([compiler, '/nologo', '/c', '/Fo' + tmpo, tmpc])
    subprocess.check_call([linker, '/NOLOGO', '/OUT:' + outa, tmpo])
else:
    subprocess.check_call([compiler, '-c', '-o', tmpo, tmpc])
    subprocess.check_call([linker, 'csr', outa, tmpo])

os.unlink(tmpo)
os.unlink(tmpc)

