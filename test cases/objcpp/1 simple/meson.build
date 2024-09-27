project('Objective C++', 'objcpp', default_options: 'cpp_std=c++14')

if get_option('backend').startswith('vs')
  error('MESON_SKIP_TEST: objcpp is not supported by vs backend')
endif

exe = executable('objcppprog', 'prog.mm')
test('objcpp', exe)
