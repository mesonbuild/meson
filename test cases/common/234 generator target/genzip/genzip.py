#!/usr/bin/env python3

import os, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ofilename = sys.argv[1]
ofiletmpname = ofilename + '.tmp'
infiles = sys.argv[2:]

with zipfile.ZipFile(ofiletmpname, 'w') as zf:
    for xmlfilename in infiles:
        xmlfile = Path(xmlfilename)
        zf.write(xmlfilename, xmlfile.name())

if os.path.exists(ofilename):
    os.unlink(ofilename)

os.rename(ofiletmpname, ofilename)
