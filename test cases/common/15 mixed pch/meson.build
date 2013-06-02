project('mixed C and C++ pch test', 'cpp', 'c')

pch = ['pch/main.hh', 'pch/func.h']

exe = executable('prog', 'main.cc', 'func.c', pch : pch)
