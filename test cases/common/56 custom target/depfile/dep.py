#!/usr/bin/env python3

import sys, os
from glob import glob

_, srcdir, depfile, output = sys.argv

depfiles = glob(os.path.join(srcdir, '*'))

quoted_depfiles = [x.replace(' ', '\ ') for x in depfiles]

open(output, 'w').write('I am the result of globbing.')
open(depfile, 'w').write('%s: %s\n' % (output, ' '.join(quoted_depfiles)))
