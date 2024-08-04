project('objective c args', 'objc')

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objc is not supported by vs backend')
endif

exe = executable('prog', 'prog.m', objc_args : ['-DMESON_TEST'])
test('objective c args', exe)
