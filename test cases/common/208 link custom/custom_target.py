#!/usr/bin/env python3

import shutil
import sys

if __name__ == '__main__':
    shutil.copyfile(sys.argv[1], sys.argv[2])
