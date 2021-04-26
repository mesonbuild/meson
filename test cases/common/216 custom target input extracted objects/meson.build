project('custom target input extracted objects', 'c')

if meson.backend() == 'xcode'
    error('MESON_SKIP_TEST: sometimes Xcode puts object files in weird paths and we can not extract them.')
endif


checker = find_program('check_object.py')

cc = meson.get_compiler('c').cmd_array().get(-1)

subdir('libdir')

custom_target('check',
  input: objlib.extract_objects('source.c'),
  output: 'objcheck',
  command: [checker, '@INPUT@', '@OUTPUT@'],
  build_by_default: true)
