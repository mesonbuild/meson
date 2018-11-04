exe = executable(
  'prog',
  files('main.cc', 'func.c'),
  c_pch : ['pch/func.h', 'pch/func_pch.c'],
  cpp_pch : ['pch/main_pch.cc', 'pch/main.h'],
)

# test pch when only a header is given (not supported by msvc)
cc = meson.get_compiler('c')
if not ['msvc', 'clang-cl'].contains(cc.get_id())
  exe2 = executable(
    'prog2',
    files('main.cc', 'func.c'),
    c_pch : 'pch/func.h',
    cpp_pch : 'pch/main.h',
  )
endif
