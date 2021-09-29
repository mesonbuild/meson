#!/usr/bin/env python3

from pathlib import Path
import typing as T

root = Path(__file__).absolute().parent
mesonbuild = root / 'mesonbuild'

whitelist = ['mesonbuild/', 'run_', 'ci/', 'tools/', 'docs/']

def check_missing_encoding(lines: T.List[str], path: str) -> int:
    errors = 0
    functions = ['read_text', 'write_text', 'open']
    for num, line in enumerate(lines):
        for func in functions:
            l = line

            # Skip ignored lines
            if '[ignore encoding]' in l:
                continue

            # Do we have a match?
            loc = l.find(func + '(')
            if loc < 0:
                continue
            if loc > 0 and ord(l[loc-1].lower()) in [*range(ord('a'), ord('z')), *range(ord('0'), ord('9')), '_']:
                continue
            loc += len(func) + 1
            # Some preprocessign to make parsing easier
            l = l[loc:]
            l = l.replace(' ', '')
            l = l.replace('\t', '')
            l = l.replace('\n', '')
            l = l.replace('\'', '"')

            # Parameter begin
            args = ''
            b_open = 1
            while l:
                c = l[0]
                l = l[1:]
                if c == ')':
                    b_open -= 1
                if b_open == 0:
                    break
                elif b_open == 1:
                    args += c
                if c == '(':
                    b_open += 1

            binary_modes = ['rb', 'br', 'r+b', 'wb', 'bw', 'ab', 'ba']
            is_binary = any([f'"{x}"' in args for x in binary_modes])
            if 'encoding=' not in args and not (func == 'open' and is_binary):
                location = f'\x1b[33;1m[\x1b[0;1m{path}:{num+1}\x1b[33m]\x1b[0m'
                #print(f'{location:<64}: \x1b[31;1mERROR:\x1b[0m Missing `encoding=` parameter in "{line.strip()}"')
                print(f'{location:<72}: \x1b[31;1mERROR:\x1b[0m Missing `encoding=` parameter in `{func}` call')
                errors += 1
    return errors

def main() -> int:
    print('Scanning mesonbuild...')
    errors = 0
    for i in sorted(root.glob('**/*.py')):
        raw = i.read_text(encoding='utf-8')
        lines = raw.splitlines()
        filename = i.relative_to(root).as_posix()

        if not any([filename.startswith(x) for x in whitelist]):
            continue

        errors += check_missing_encoding(lines, filename)
    print(f'Found {errors} errors while scanning mesonbuild')
    return 0 if errors == 0 else 1

if __name__ == '__main__':
    raise SystemExit(main())
