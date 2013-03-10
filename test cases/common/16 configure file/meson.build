project('configure file test', 'c')

var = 'mystring'
other = 'string 2'
second = ' bonus'
BE_TRUE = true

configure_file('config.h.in', 'config.h')

e = executable('inctest', 'prog.c', include_dirs : include_directories('.'))
add_test('inctest', e)
