project(
  'invalid C standard overriden to valid one',
  'c',
  default_options : ['c_std=invalid99'],
)

exe = executable('main', 'main.c')
test('main', exe)
