project('extract all', 'c', 'cpp')

a = static_library('a', 'one.c', 'two.c')
b = static_library('b', 'three.c', 'four.c')
c = shared_library('c',
  objects : [a.extract_all_objects(), b.extract_all_objects()],
  vs_module_defs : 'func1234.def')

e = executable('proggie', 'prog.c', link_with : c)
test('extall', e)
