project('endian check', 'c')

if host.is_big_endian()
  add_global_arguments('c', '-DIS_BE')
endif

test('endiantest', executable('prog', 'prog.c'))
