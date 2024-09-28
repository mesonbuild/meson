project('objective c++ args', 'objcpp')

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objcpp is not supported by vs backend')
endif

exe = executable('prog', 'prog.mm', objcpp_args : ['-DMESON_OBJCPP_TEST'])
test('objective c++ args', exe)
