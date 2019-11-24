#! /usr/bin/python

import os

assert(os.environ['MESON_UNINSTALLED'] == '1')
assert(os.environ['TEST_A'] == '1')
assert(os.environ['TEST_B'] == '0+1+2+3')
