project('local arg test', 'cxx', 'c')

exe1 = executable('prog', 'prog.cc', 'func.c', \
c_args   : '-DCTHING', \
cxx_args : '-DCXXTHING')

add_test('prog1', exe1)
