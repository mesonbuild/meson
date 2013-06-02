project('global arg test', 'cxx', 'c')

add_global_arguments('-DMYTHING', language : 'c')
add_global_arguments('-DMYCXXTHING', language : 'cxx')

exe1 = executable('prog', 'prog.c')
exe2 = executable('prog2', 'prog.cc')

test('prog1', exe1)
test('prog2', exe2)

