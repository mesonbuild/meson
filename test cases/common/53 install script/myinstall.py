#!/usr/bin/env python3

import argparse
import os
import shutil

prefix = os.environ['MESON_INSTALL_DESTDIR_PREFIX']


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('dirname')
    parser.add_argument('files', nargs='+')
    parser.add_argument('--mode', action='store', default='create', choices=['create', 'copy'])
    args = parser.parse_args()

    dirname = os.path.join(prefix, args.dirname)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if args.mode == 'create':
        for name in args.files:
            with open(os.path.join(dirname, name), 'w') as f:
                f.write('')
    else:
        for name in args.files:
            shutil.copy(name, dirname)


if __name__ == "__main__":
    main()
