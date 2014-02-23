project('sub sub', 'c')

a = subproject('a')
lib = a.get_variable('l')

exe = executable('prog', 'prog.c', link_with : lib)
test('basic', exe)