project('Python extension module', 'c')

py3_dep = dependency('python3')

subdir('ext')

test('extmod',
  find_program('blaster.py'),
  env : ['PYTHONPATH=' + pypathdir])
