#!/usr/bin/env python
"""Test script that checks if zlib was statically linked to executable"""
import subprocess
import sys

def main():
    """Main function"""
    output = subprocess.check_output(['nm', sys.argv[1]]).decode('utf-8')

    if 'T zlibVersion' in output:
        sys.exit(0)

    sys.exit(1)

if __name__ == '__main__':
    main()
