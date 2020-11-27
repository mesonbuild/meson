#!/usr/bin/env python3

import os, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ifile = Path(sys.argv[1])
ofilename = sys.argv[2]

compname = ifile.read_text().strip()
root = ET.Element('component')
root.text = compname
tree = ET.ElementTree(root)
tree.write(ofilename, encoding='utf-8', xml_declaration=True)
