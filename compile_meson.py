#!/usr/bin/python3 -tt

# This file generates all files needed to run
# Meson. It does the equivalent of "make" in
# standard build systems.

import os
import mparser

fullfile = os.path.abspath(__file__)
fulldir = os.path.dirname(fullfile)

mparser.generate_parser_files(fulldir)
