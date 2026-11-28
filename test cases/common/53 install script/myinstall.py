#!/usr/bin/env python3

import argparse
import os
import shutil

prefix = os.environ['MESON_INSTALL_DESTDIR_PREFIX']
dry_run = bool(os.environ.get('MESON_INSTALL_DRY_RUN'))
install_log_file = os.environ.get('MESON_INSTALL_LOG_FILE')

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('dirname')
    parser.add_argument('files', nargs='+')
    parser.add_argument('--mode', action='store', default='create', choices=['create', 'copy'])
    args = parser.parse_args()

    dirname = os.path.join(prefix, args.dirname)
    if not os.path.exists(dirname):
        if dry_run:
            print(f"DRYRUN: Creating directory {dirname}")
        else:
            os.makedirs(dirname)

    if args.mode == 'create':
        for name in args.files:
            install_file = os.path.join(dirname, name)
            # Write file paths to the log even on dry runs
            with open(install_log_file, 'a', encoding='utf-8') as log:
                log.write(install_file + '\n')

            if dry_run:
                print(f'DRYRUN: Writing file {name}')
            else:
                with open(install_file, 'w', encoding='utf-8') as f:
                    f.write('')
    else:
        for name in args.files:
            if dry_run:
                print(f"DRYRUN: Copying file {name} to {dirname}")
            else:
                shutil.copy(name, dirname)


if __name__ == "__main__":
    main()
