#!/usr/bin/env python3

import os, sys, zipfile

expected_files = {'first.xlc',
                  'second.xlc',
                  'third.xlc'}

def validate(zfname):
    with zipfile.ZipFile(zfname, 'r') as zf:
        namelist = zf.namelist()
        if len(namelist) != 3:
            sys.exit('Incorrect number of entries in zipfile')
        for i in namelist:
            if i not in expected_files:
                sys.exit('Unexpected file {}.'.format(i))
    sys.exit('Not done yet')

if __name__ == '__main__':
    validate(sys.argv[1])
