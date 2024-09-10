#!/usr/bin/env python3
#
# User-specified config-tool, must implement --cflags, --libs, and --version
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
    flag = sys.argv[1]

    if flag == '--cflags':
        somedep = pathlib.Path(__file__).parent / 'somedep'
        print(make_include_arg(somedep))
    elif flag == '--libs':
        print()
    elif flag == '--version':
        print('42.0')
    else:
        sys.exit(1)
