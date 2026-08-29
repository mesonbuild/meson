#!/usr/bin/env python3

import ctypes
import sys

mylib = ctypes.cdll.LoadLibrary(sys.argv[1])
assert mylib.foo() == 42
