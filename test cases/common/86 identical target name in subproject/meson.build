project('toplevel bar', 'c')

subproject('foo')

executable('bar', 'bar.c')
run_target('nop', command : ['true'])
custom_target('cus', output: ['cus.c'], command : ['true'])
