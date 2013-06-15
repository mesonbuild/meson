project('mixed C and C++ pch test', 'cpp', 'c')


exe = executable('prog', 'main.cc', 'func.c',
c_pch : ['pch/func.h', 'pch/func_pch.c'],
cpp_pch : ['pch/main_pch.cc', 'pch/main.h'])
