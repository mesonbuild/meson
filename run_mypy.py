#!/usr/bin/env python3

import sys
import subprocess
import argparse
from pathlib import Path
import typing as T

modules = [
  # fully typed submodules
  'mesonbuild/ast',
  'mesonbuild/scripts',
  'mesonbuild/wrap',

  # specific files
  'mesonbuild/arglist.py',
  'mesonbuild/compilers/compilers.py',
  'mesonbuild/compilers/mixins/arm.py',
  'mesonbuild/compilers/mixins/c2000.py',
  'mesonbuild/compilers/mixins/ccrx.py',
  'mesonbuild/compilers/mixins/clang.py',
  'mesonbuild/compilers/mixins/clike.py',
  'mesonbuild/compilers/mixins/compcert.py',
  'mesonbuild/compilers/mixins/elbrus.py',
  'mesonbuild/compilers/mixins/emscripten.py',
  'mesonbuild/compilers/mixins/gnu.py',
  'mesonbuild/compilers/mixins/intel.py',
  'mesonbuild/compilers/mixins/islinker.py',
  'mesonbuild/compilers/mixins/pgi.py',
  # 'mesonbuild/coredata.py',
  'mesonbuild/dependencies/boost.py',
  'mesonbuild/dependencies/hdf5.py',
  'mesonbuild/dependencies/mpi.py',
  'mesonbuild/envconfig.py',
  'mesonbuild/interpreterbase.py',
  'mesonbuild/linkers.py',
  'mesonbuild/mcompile.py',
  'mesonbuild/mesonlib.py',
  'mesonbuild/minit.py',
  'mesonbuild/mintro.py',
  'mesonbuild/mlog.py',
  'mesonbuild/modules/fs.py',
  'mesonbuild/mparser.py',
  'mesonbuild/msetup.py',
  'mesonbuild/mtest.py',

  'run_mypy.py',
  'tools'
]

def check_mypy() -> None:
  try:
    import mypy
  except ImportError:
    print('Failed import mypy')
    sys.exit(1)

def main() -> int:
  check_mypy()

  root = Path(__file__).absolute().parent
  args = []  # type: T.List[str]

  parser = argparse.ArgumentParser(description='Process some integers.')
  parser.add_argument('-p', '--pretty', action='store_true', help='pretty print mypy errors')

  opts = parser.parse_args()
  if opts.pretty:
    args.append('--pretty')

  p = subprocess.run(
    [sys.executable, '-m', 'mypy'] + args + modules,
    cwd=root,
  )
  return p.returncode

if __name__ == '__main__':
  sys.exit(main())
