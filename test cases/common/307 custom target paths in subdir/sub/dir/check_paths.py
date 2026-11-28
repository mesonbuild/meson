#!/usr/bin/env python3

import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--source-root', required=True)
parser.add_argument('--build-root', required=True)
parser.add_argument('--current-source-dir', required=True)
parser.add_argument('--private-dir', required=True)
parser.add_argument('--source-file', required=True)
parser.add_argument('--built-file', required=True)
parser.add_argument('--custom-target-arg', required=True)
parser.add_argument('--input', nargs='+', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()

errors = []


def check(what: str, path: str) -> None:
    if not os.path.exists(path):
        errors.append(f'{what}: {path!r} does not exist (cwd: {os.getcwd()!r})')


check('source root', os.path.join(args.source_root, 'sub', 'dir', 'check_paths.py'))
check('build root', os.path.join(args.build_root, 'meson-private'))
check('current source dir', os.path.join(args.current_source_dir, 'check_paths.py'))
check('private dir', args.private_dir)
check('source file', args.source_file)
check('built file', args.built_file)
check('custom target argument', args.custom_target_arg)
for i in args.input:
    check('input', i)

if errors:
    sys.exit('\n'.join(errors))

with open(args.output, 'w', encoding='utf-8') as f:
    f.write('ok\n')
