# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2024 Contributors to the The Meson project

from . import mlog

class MachineFile:
    def __init__(self, fname):
        with open(fname, encoding='utf-8') as f:
            pass
        self.stuff = None

class MachineFileStore:
    def __init__(self, native_files, cross_files):
        self.native = [MachineFile(x) for x in native_files]
        self.cross = [MachineFile(x) for x in cross_files]
