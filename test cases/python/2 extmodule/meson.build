project('Python extension module', 'c',
  default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Ninja backend required')
endif


py_mod = import('python')
py = py_mod.find_installation()
py_dep = py.dependency(required: false)

if not py_dep.found()
  error('MESON_SKIP_TEST: Python libraries not found.')
endif

subdir('ext')

test('extmod',
  py,
  args : files('blaster.py'),
  env : ['PYTHONPATH=' + pypathdir])


py3_pkg_dep = dependency('python3', method: 'pkg-config', required : false)
if py3_pkg_dep.found()
  python_lib_dir = py3_pkg_dep.get_pkgconfig_variable('libdir')

  # Check we can apply a version constraint
  dependency('python3', version: '>=@0@'.format(py_dep.version()))
else
  message('Skipped python3 pkg-config test')
endif
