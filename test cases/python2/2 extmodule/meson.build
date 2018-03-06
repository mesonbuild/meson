project('Python extension module', 'c',
  default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

py2_mod = import('python2')
py2 = py2_mod.find_python()
py2_dep = dependency('python2', required : false)

if py2_dep.found()
  subdir('ext')

  test('extmod',
    py2,
    args : files('blaster.py'),
    env : ['PYTHONPATH=' + pypathdir])
else
  error('MESON_SKIP_TEST: Python2 libraries not found, skipping test.')
endif

py2_pkg_dep = dependency('python2', method: 'pkg-config', required : false)
if py2_pkg_dep.found()
  python_lib_dir = py2_pkg_dep.get_pkgconfig_variable('libdir')
endif
