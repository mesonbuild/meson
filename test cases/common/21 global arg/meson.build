project('global arg test', 'cpp', 'c')

add_global_arguments('-DMYTHING', language : 'c')
add_global_arguments('-DMYCPPTHING', language : 'cpp')

add_global_arguments('-DGLOBAL_NATIVE', language : 'c', native : true)
add_global_arguments('-DGLOBAL_CROSS', language : 'c', native : false)

if meson.is_cross_build()
  c_args = ['-DARG_CROSS']
else
  c_args = ['-DARG_NATIVE']
endif

add_global_arguments('-DMYCANDCPPTHING', language: ['c', 'cpp'])

exe1 = executable('prog', 'prog.c', c_args : c_args)
exe2 = executable('prog2', 'prog.cc')

test('prog1', exe1)
test('prog2', exe2)

