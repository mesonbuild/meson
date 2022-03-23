project('cython_args', ['cython', 'c'])

pymod = import('python')
python = pymod.find_installation('python3')
python_dep = python.dependency()
if not python_dep.found()
  error('MESON_SKIP_TEST: Python library not found.')
endif

mod = python.extension_module(
  'cythonargs',
  files('cythonargs.pyx'),
  cython_args: [
    '--compile-time-env',
    'VALUE=1'
  ],
  dependencies: [python_dep]
)

test(
  'test',
  python,
  args: [
    'test.py'
  ],
  workdir: meson.current_source_dir(),
  env: environment({
    'PYTHONPATH': meson.current_build_dir(),
  })
)
