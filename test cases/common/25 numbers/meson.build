project('numbers', 'c')

if host.pointer_size() == 64
  add_global_arguments('-DIS64', language : 'c')
endif

test('sizetest', executable('prog', 'prog.c'))
