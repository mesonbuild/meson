#!/usr/bin/env python3

import sys, os, subprocess

def generate(infile, outfile, fallback):
    workdir = os.path.split(infile)[0]
    if workdir == '':
        workdir = '.'
    version = fallback
    try:
        p = subprocess.Popen(['git', 'describe'], cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdo, _) = p.communicate()
        if p.returncode == 0:
            version = stdo.decode().strip()
    except:
        pass
    newdata = open(infile).read().replace('@VERSION@', version)
    try:
        olddata = open(outfile).read()
        if olddata == newdata:
            return
    except:
        pass
    open(outfile, 'w').write(newdata)

if __name__ == '__main__':
    infile = sys.argv[1]
    outfile = sys.argv[2]
    fallback = sys.argv[3]
    generate(infile, outfile, fallback)
