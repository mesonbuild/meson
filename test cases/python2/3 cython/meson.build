project('cython', 'c',
  default_options : ['warning_level=3'])

cython = find_program('cython2', required : false)

if not cython.found()
  # Named that way on Ubuntu Trusty
  cython = find_program('cython', required: false)
endif

py2_dep = dependency('python2', required : false)

if cython.found() and py2_dep.found()
  py2_dep = dependency('python2')
  py2_mod = import('python2')
  py2 = py2_mod.find_python()
  subdir('libdir')

  test('cython tester',
    py2,
    args : files('cytest.py'),
    env : ['PYTHONPATH=' + pydir]
  )
else
  error('MESON_SKIP_TEST: Cython2 or Python2 libraries not found, skipping test.')
endif
