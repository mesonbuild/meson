#!/usr/bin/env python

import os
import sys

if not os.path.isfile(sys.argv[1]):
    raise Exception("Couldn't find {!r}".format(sys.argv[1]))
