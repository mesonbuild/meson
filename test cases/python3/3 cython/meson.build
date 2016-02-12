project('cython', 'c',
  default_options : ['warning_level=3'])

cython = find_program('cython3')
py3_dep = dependency('python3')

subdir('libdir')

test('cython tester',
  find_program('cytest.py'),
  env : ['PYTHONPATH=' + pydir]
)
