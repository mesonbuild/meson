project('header in file list', 'c')

exe = executable('prog', 'prog.c', 'header.h')
add_test('basic', exe)
