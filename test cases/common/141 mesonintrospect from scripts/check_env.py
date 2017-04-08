#!/usr/bin/env python3

import os
import sys

do_print = False

if len(sys.argv) > 1:
    do_print = bool(sys.argv[1])

if 'MESONINTROSPECT' not in os.environ:
    raise RuntimeError('MESONINTROSPECT not found')

mesonintrospect = os.environ['MESONINTROSPECT']

if not os.path.isfile(mesonintrospect):
    raise RuntimeError('{!r} does not exist'.format(mesonintrospect))

if do_print:
    print(mesonintrospect, end='')
