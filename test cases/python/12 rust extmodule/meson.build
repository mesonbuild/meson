project('Python extension module', 'c',
  default_options : ['buildtype=release', 'werror=true', 'python.bytecompile=-1'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Ninja backend required')
endif
if not add_languages('rust', required: false, native: false)
  error('MESON_SKIP_TEST: Rust compiler required')
endif

py_mod = import('python')
py = py_mod.find_installation()
py_dep = py.dependency(required: false)

if not py_dep.found()
  error('MESON_SKIP_TEST: Python libraries not found.')
endif

# Rust code cannot rely on #define PyModule_Create, so it calls
# PyModule_Create2.  But it is also not possible to use has_function()
# because the function is in the Python executable, so just check
# for PyPy.
if run_command(py, '-c', 'import sys; sys.exit("__pypy__" in sys.builtin_module_names)',
               check: false).returncode() == 1
  error('MESON_SKIP_TEST: Limited API not supported (PyPy?)')
endif

subdir('ext')

src = files('blaster.py')
test('extmod',
  py,
  args : src,
  env : ['PYTHONPATH=' + pypathdir])
