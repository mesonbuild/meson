#!/usr/bin/env python
import sys

assert len(sys.argv) == 3
assert sys.argv[1] in {'thin', 'fat'}

FAT_MAGIC  = b'!<arch>\n'
THIN_MAGIC = b'!<thin>\n'
magic = open(sys.argv[2], 'rb').read(8)


# Check if signature of archive is as expected
if sys.argv[1] == 'thin':
    if   magic.startswith(THIN_MAGIC): sys.exit(0)
    elif magic.startswith(FAT_MAGIC):  sys.exit(1)
else:
    if   magic.startswith(THIN_MAGIC): sys.exit(1)
    elif magic.startswith(FAT_MAGIC):  sys.exit(0)


# Inconclusive test, probably an unknown or foreign static archive format.
# Allow check to pass
sys.exit(0)
