#!/usr/bin/python3 -tt

# Copyright 2013 Jussi Pakkanen

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, pickle, os, shutil

class InstallData():
    def __init__(self):
        self.targets = []

def do_install(datafilename):
    ifile = open(datafilename, 'rb')
    d = pickle.load(ifile)
    for t in d.targets:
        fullfilename = t[0]
        outdir = t[1]
        fname = os.path.split(fullfilename)[1]
        outname = os.path.join(outdir, fname)
        print('Copying %s to %s' % (fname, outdir))
        os.makedirs(outdir, exist_ok=True)
        shutil.copyfile(fullfilename, outname)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Installer script for Builder. Do not run on your own, mmm\'kay?')
        print('%s [install info file]' % sys.argv[0])
    datafilename = sys.argv[1]
    do_install(datafilename)

