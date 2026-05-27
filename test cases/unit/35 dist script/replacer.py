#!/usr/bin/env python3

import os
import pathlib
import sys

if len(sys.argv) < 3:
    sys.exit('usage: replacer.py <pattern> <replacement>')

source_root = pathlib.Path(os.environ['MESON_DIST_ROOT'])

modfile = source_root / 'prog.c'

contents = modfile.read_text(encoding='utf-8')
contents = contents.replace(sys.argv[1], sys.argv[2])
modfile.write_text(contents, encoding='utf-8')
