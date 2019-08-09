project('custom target input extracted objects', 'c')

checker = find_program('check_object.py')
verify = find_program('verify.py')

cc = meson.get_compiler('c').cmd_array().get(-1)

subdir('libdir')

result = custom_target('check',
  input: objlib.extract_objects('source.c'),
  output: 'objcheck',
  command: [checker, '@INPUT@', '@OUTPUT@'],
  build_by_default: true)

test('verify', verify, args: result)
