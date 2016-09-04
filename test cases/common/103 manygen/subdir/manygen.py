#!/usr/bin/env python3

# Generates a static library, object file, source
# file and a header file.

import sys, os
import shutil, subprocess

with open(sys.argv[1]) as f:
    funcname = f.readline().strip()
outdir = sys.argv[2]

if not os.path.isdir(outdir):
    print('Outdir does not exist.')
    sys.exit(1)

# Emulate the environment.detect_c_compiler() logic
compiler = os.environ.get('CC', None)
if not compiler:
    compiler = shutil.which('cl') or \
        shutil.which('gcc') or \
        shutil.which('clang') or \
        shutil.which('cc')

compbase = os.path.basename(compiler)
if 'cl' in compbase and 'clang' not in compbase:
    libsuffix = '.lib'
    is_vs = True
    compiler = 'cl'
    linker = 'lib'
else:
    libsuffix = '.a'
    is_vs = False
    linker = 'ar'
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

with open(outc, 'w') as f:
    f.write('''#include"%s.h"
int %s_in_src() {
  return 0;
}
''' % (funcname, funcname))

with open(outh, 'w') as f:
    f.write('''#pragma once
int %s_in_lib();
int %s_in_obj();
int %s_in_src();
''' % (funcname, funcname, funcname))

with open(tmpc, 'w') as f:
    f.write('''int %s_in_obj() {
  return 0;
}
''' % funcname)

if is_vs:
    subprocess.check_call([compiler, '/nologo', '/c', '/Fo' + outo, tmpc])
else:
    subprocess.check_call([compiler, '-c', '-o', outo, tmpc])

with open(tmpc, 'w') as f:
    f.write('''int %s_in_lib() {
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

