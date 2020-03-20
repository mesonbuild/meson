import sys
from gluon import gluonator

with open(sys.argv[1], 'w') as out:
    print('hello %s' % gluonator.gluoninate(), file=out)
