#!/usr/bin/env python3

import os, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ifilename = sys.argv[1]
ofilename = sys.argv[2]

intree = ET.parse(ifilename)
inroot = intree.root()

component_name = inroot.text
localized_name = 'le_' + component_name

outroot = ET.Element('component', {'name': component_name,
                                   'localized_name': localized_name})
tree = ET.ElementTree(root)
tree.write(ofilename, encoding='utf-8', xml_declaration=True)
