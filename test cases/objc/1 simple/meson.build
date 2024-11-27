project('objective c', 'objc', default_options: ['c_std=c99'])

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objc is not supported by vs backend')
endif

exe = executable('prog', 'prog.m')
test('objctest', exe)
