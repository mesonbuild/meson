#!/usr/bin/env python3
#
# User-specified config-tool that has custom positional arguments. must implement --cflags,
# --libs, and --version
#
# Note: meson will not reconfigure if this program or its output changes
#    

import pathlib
import platform
import sys


def make_include_arg(p: pathlib.Path) -> str:
    if platform.system().lower() == "windows":
        return f'"-I{p.absolute()}"'
    else:
        return f"'-I{p.absolute()}'"


if __name__ == '__main__':
    _, module, flag = sys.argv

    # pretend we can only find somemod module
    if module != 'somemod':
        sys.exit(1)

    if flag == '--cflags':
        somemod = pathlib.Path(__file__).parent / 'somemod'
        print(make_include_arg(somemod))
    elif flag == '--libs':
        print()
    elif flag == '--version':
        print('43.0')
    else:
        sys.exit(1)
