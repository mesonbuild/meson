#!/usr/bin/env python3

import re
import subprocess
import sys

tool = sys.argv[1]
executable = sys.argv[2]
expected = int(sys.argv[3])
actual = -1

if 'objdump' in tool:
    result = subprocess.check_output([tool, '-p', executable]).decode()
    match = re.search(r'^Subsystem\s+(\d+)', result, re.MULTILINE)
elif 'dumpbin' in tool:
    result = subprocess.check_output([tool, '/headers', executable]).decode()
    match = re.search(r'^\s*(\d+) subsystem(?! version)', result, re.MULTILINE)
else:
    print('unknown tool')
    sys.exit(1)

if match:
    actual = int(match.group(1))

print('subsystem expected: %d, actual: %d' % (expected, actual))
sys.exit(0 if (expected == actual) else 1)
