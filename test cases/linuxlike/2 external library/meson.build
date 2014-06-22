project('external library', 'c')

zlib = find_library('z')
e = executable('zprog', 'prog.c', dependencies : zlib)
test('libtest', e)
