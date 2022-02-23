#! /usr/bin/python

import os
from pathlib import Path

assert os.environ['MESON_DEVENV'] == '1'
assert os.environ['MESON_PROJECT_NAME'] == 'devenv'
assert os.environ['TEST_A'] == '1'
assert os.environ['TEST_B'] == '0+1+2+3+4'

from mymod.mod import hello
assert hello == 'world'

from mymod2.mod2 import hello
assert hello() == 42
