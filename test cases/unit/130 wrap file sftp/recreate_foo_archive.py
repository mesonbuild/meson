#!/usr/bin/env python3

# This script can be used to recreate the test archive.

import tarfile
import time

def set_mtime(tarinfo):
    tarinfo.mtime = 0
    return tarinfo

# To avoid updated timestamps alone causing a diff in the archive, make sure
# the gzip header has mtime 0, and also set mtime 0 for the members.
time.time = lambda: 0
with tarfile.open('foo.tar.gz', 'w:gz') as archive:
    archive.add('foo/foo.c', filter=set_mtime)
    archive.add('foo/foo.h', filter=set_mtime)
    archive.add('foo/meson.build', filter=set_mtime)
