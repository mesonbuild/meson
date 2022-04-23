project('trivial test', 'c')

py_inst = import('python').find_installation()

exe = executable('trivialprog', 'trivial.c')
runt = run_target('invalid', command: [py_inst, '--version'])
test('runtest', exe, args: runt)
