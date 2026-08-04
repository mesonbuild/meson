#!/usr/bin/env python3
import sys

with open(sys.argv[1], encoding='utf-8') as f:
    libs_line = next(line for line in f if line.startswith('Libs:')).strip()

assert '-lstaticlib' in libs_line, f'staticlib missing from Libs: {libs_line!r}'
assert 'proc_macro_examples' not in libs_line, \
    f'proc-macro wrongly listed in Libs: {libs_line!r}'
print(f'OK: {libs_line}')
