project('Python extension module', 'c',
  default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

py3_mod = import('python3')
py3 = py3_mod.find_python()
py3_dep = dependency('python3', required : false)

if py3_dep.found()
  subdir('ext')

  test('extmod',
    py3,
    args : files('blaster.py'),
    env : ['PYTHONPATH=' + pypathdir])
else
  error('MESON_SKIP_TEST: Python3 libraries not found, skipping test.')
endif

py3_pkg_dep = dependency('python3', method: 'pkg-config', required : false)
if py3_pkg_dep.found()
  python_lib_dir = py3_pkg_dep.get_pkgconfig_variable('libdir')
endif
