project('global arg test', 'cpp', 'c')

add_global_arguments('-DMYTHING', language : 'c', native : true)
add_global_arguments('-DMYTHING', language : 'c', native : false)
add_global_arguments('-DMYCPPTHING', language : 'cpp', native : true)
add_global_arguments('-DMYCPPTHING', language : 'cpp', native : false)

add_global_arguments('-DGLOBAL_BUILD', language : 'c', native : true)
add_global_arguments('-DGLOBAL_HOST', language : 'c', native : false)

build_c_args = ['-DARG_BUILD']
c_args = ['-DARG_HOST']

add_global_arguments('-DMYCANDCPPTHING', language: ['c', 'cpp'], native: true)
add_global_arguments('-DMYCANDCPPTHING', language: ['c', 'cpp'], native: false)

exe1 = executable('prog1', 'prog.c', c_args : build_c_args, native : true)
exe2 = executable('prog2', 'prog.c', c_args : c_args, native : false)
exe3 = executable('prog3', 'prog.cc')

test('prog1', exe1)
test('prog2', exe2)
test('prog3', exe3)
