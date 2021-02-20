#! /usr/bin/python

import os

assert(os.environ['MESON_DEVENV'] == '1')
assert(os.environ['MESON_PROJECT_NAME'] == 'devenv')
assert(os.environ['TEST_A'] == '1')
assert(os.environ['TEST_B'] == '1+2+3')
