project('cython', 'c',
  default_options : ['warning_level=3'])

cython = find_program('cython3', required : false)

if cython.found()
  py3_dep = dependency('python3')

  subdir('libdir')

  test('cython tester',
    find_program('cytest.py'),
    env : ['PYTHONPATH=' + pydir]
  )
else
  error('MESON_SKIP_TEST: Cython not found, skipping test.')
endif
