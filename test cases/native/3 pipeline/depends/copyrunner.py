#!/usr/bin/env python3

import sys
import subprocess

prog, infile, outfile = sys.argv[1:]

subprocess.check_call([prog, infile, outfile])
