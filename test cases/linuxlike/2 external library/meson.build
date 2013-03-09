project('external library', 'c')

zlib = find_library('z', required : true)
e = executable('zprog', 'prog.c', deps : zlib)
add_test('libtest', e)
