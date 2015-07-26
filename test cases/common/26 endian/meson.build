project('endian check', 'c')

if host.is_big_endian()
  add_global_arguments('-DIS_BE', language : 'c')
endif

test('endiantest', executable('prog', 'prog.c'))
