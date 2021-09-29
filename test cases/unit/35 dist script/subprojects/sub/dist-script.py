#!/usr/bin/env python3

import os
import pathlib
import sys

assert sys.argv[1] == 'success'

source_root = pathlib.Path(os.environ['MESON_PROJECT_DIST_ROOT'])
modfile = source_root / 'prog.c'
with modfile.open('w') as f:
    f.write('int main(){return 0;}')
