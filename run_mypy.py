#!/usr/bin/env python3

import sys
import subprocess
import argparse
from pathlib import Path
import typing as T

normal_modules = [
  'mesonbuild/interpreterbase.py',
  'mesonbuild/mtest.py',
  'mesonbuild/minit.py',
  'mesonbuild/mintro.py',
  'mesonbuild/mparser.py',
  'mesonbuild/msetup.py',
  'mesonbuild/ast',
  'mesonbuild/wrap',
  'tools',
  'mesonbuild/modules/fs.py',
  'mesonbuild/dependencies/boost.py',
  'mesonbuild/dependencies/mpi.py',
  'mesonbuild/dependencies/hdf5.py',
  'mesonbuild/compilers/mixins/intel.py',
  'mesonbuild/mlog.py',
  'mesonbuild/mcompile.py',
  'mesonbuild/mesonlib.py',
  'mesonbuild/arglist.py',
  # 'mesonbuild/envconfig.py',
]

strict_modules = [
  'mesonbuild/interpreterbase.py',
  'mesonbuild/mparser.py',
  'mesonbuild/mesonlib.py',
  'mesonbuild/mlog.py',
  'mesonbuild/ast',
  # 'mesonbuild/wrap',
  'run_mypy.py',
]

normal_args = ['--follow-imports=skip']
strict_args = normal_args + [
  '--warn-redundant-casts',
  '--warn-unused-ignores',
  '--warn-return-any',
  # '--warn-unreachable',
  '--disallow-untyped-calls',
  '--disallow-untyped-defs',
  '--disallow-incomplete-defs',
  '--disallow-untyped-decorators',
  '--no-implicit-optional',
  '--strict-equality',
  # '--disallow-any-expr',
  # '--disallow-any-decorated',
  # '--disallow-any-explicit',
  # '--disallow-any-generics',
  # '--disallow-subclassing-any',
]

def run_mypy(opts: T.List[str], modules: T.List[str]) -> int:
  root = Path(__file__).absolute().parent
  p = subprocess.run(
    [sys.executable, '-m', 'mypy'] + opts + modules,
    cwd=root,
  )
  return p.returncode

def check_mypy() -> None:
  try:
    import mypy
  except ImportError:
    print('Failed import mypy')
    sys.exit(1)

def main() -> int:
  res = 0
  check_mypy()

  parser = argparse.ArgumentParser(description='Process some integers.')
  parser.add_argument('-p', '--pretty', action='store_true', help='pretty print mypy errors')

  args = parser.parse_args()
  if args.pretty:
    normal_args.append('--pretty')
    strict_args.append('--pretty')

  print('Running normal mypy check...')
  res += run_mypy(normal_args, normal_modules)

  print('\n\nRunning struct mypy check...')
  res += run_mypy(strict_args, strict_modules)

  return res

if __name__ == '__main__':
  sys.exit(main())
