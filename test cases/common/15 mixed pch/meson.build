project('mixed C and C++ pch test', 'cpp', 'c')


exe = executable(
  'prog',
  files('main.cc', 'func.c'),
  c_pch : ['pch/func.h', 'pch/func_pch.c'],
  cpp_pch : ['pch/main_pch.cc', 'pch/main.h'],
)

cc = meson.get_compiler('c')
if cc.get_id() != 'msvc'
  exe2 = executable(
    'prog2',
    files('main.cc', 'func.c'),
    c_pch : 'pch/func.h',
    cpp_pch : 'pch/main.h',
  )
endif
