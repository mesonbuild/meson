project('extract all', 'c')

a = static_library('a', 'one.c', 'two.c')
b = static_library('b', 'three.c', 'four.c')
c = static_library('c', 
  objects : [a.extract_all_objects(), b.extract_all_objects()])

e = executable('proggie', 'prog.c', link_with : c)
test('extall', e)
