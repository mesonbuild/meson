#!/usr/bin/env python3

import os
import pathlib

source_root = pathlib.Path(os.environ['MESON_DIST_ROOT'])

modfile = source_root / 'prog.c'

contents = modfile.read_text()
contents = contents.replace('"incorrect"', '"correct"')
modfile.write_text(contents)
