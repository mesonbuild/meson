project('global arg test', 'cpp', 'c')

add_global_arguments('-DMYTHING', language : 'c')
add_global_arguments('-DMYCPPTHING', language : 'cpp')

add_global_arguments('-DMYCANDCPPTHING', language: ['c', 'cpp'])

exe1 = executable('prog', 'prog.c')
exe2 = executable('prog2', 'prog.cc')

test('prog1', exe1)
test('prog2', exe2)

