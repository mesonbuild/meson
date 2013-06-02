project('local arg test', 'cpp', 'c')

exe1 = executable('prog', 'prog.cc', 'func.c', \
c_args   : '-DCTHING', \
cpp_args : '-DCPPTHING')

test('prog1', exe1)
