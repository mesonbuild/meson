project('Python extension module', 'c',
  default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

py3_dep = dependency('python3')

subdir('ext')

test('extmod',
  find_program('blaster.py'),
  env : ['PYTHONPATH=' + pypathdir])
