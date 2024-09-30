#!/usr/bin/env python3
"""Test script that checks if zlib was statically linked to executable"""
import subprocess
import sys

def handle_common(path):
    """Handle the common case."""
    try:
        output = subprocess.check_output(['nm', '--defined-only', '-P', '-A', path]).decode('utf-8')
    except subprocess.CalledProcessError:
        # some NMs only support -U. Older binutils only supports --defined-only.
        output = subprocess.check_output(['nm', '-UPA', path]).decode('utf-8')
    # POSIX format. Prints all *defined* symbols, looks like this:
    # builddir/main_static: zlibVersion T 1190 39
    # or
    # builddir/main_static: zlibVersion D 1fde0 30
    if ': zlibVersion ' in output:
        return 0
    return 1

def handle_cygwin(path):
    """Handle the Cygwin case."""
    output = subprocess.check_output(['nm', path]).decode('utf-8')
    if (('I __imp_zlibVersion' in output) or ('D __imp_zlibVersion' in output)):
        return 1
    return 0

def main():
    """Main function"""
    if len(sys.argv) > 2 and sys.argv[1] == '--platform=cygwin':
        return handle_cygwin(sys.argv[2])
    else:
        return handle_common(sys.argv[2])


if __name__ == '__main__':
    sys.exit(main())
