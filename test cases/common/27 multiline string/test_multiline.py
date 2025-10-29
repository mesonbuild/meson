#! /usr/bin/env python3

import sys
import subprocess

output = subprocess.check_output(sys.argv[1:], universal_newlines=True, encoding='utf-8')

assert output == '''
Hello
World
'''
