#!/usr/bin/env python3

import os, sys
import xml.etree.ElementTree as ET
from pathlib import Path

h_templ= '''#pragma once

const char *component_{}_localized_name(void);
'''

c_templ = '''#include<{}.h>

const char *component_{}_localized_name(void) {{
    return "{}";
}}
'''

ifilename = sys.argv[1]
h_file = Path(sys.argv[2])
c_file = Path(sys.argv[3])

h_incname = h_file.name

intree = ET.parse(ifilename)
inroot = intree.root()

component_name = inroot.attrib['name']
localized_name = inroot.attrib['localized_name']

h_file.write_string(h_templ.format(component_name))
c_file.write_string(c_templ.format(h_incname, component_name, localized_name))
