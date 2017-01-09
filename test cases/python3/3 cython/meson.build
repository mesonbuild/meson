project('cython', 'c',
  default_options : ['warning_level=3'])

cython = find_program('cython3', required : false)
py3_dep = dependency('python3', required : false)

if cython.found() and py3_dep.found()
  py3_dep = dependency('python3')
  py3_mod = import('python3')
  py3 = py3_mod.find_python()
  subdir('libdir')

  test('cython tester',
    py3,
    args : files('cytest.py'),
    env : ['PYTHONPATH=' + pydir]
  )
else
  error('MESON_SKIP_TEST: Cython3 or Python3 libraries not found, skipping test.')
endif
