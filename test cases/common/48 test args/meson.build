project('test features', 'c')

e1 = executable('cmd_args', 'cmd_args.c')
e2 = executable('envvars', 'envvars.c')

test('command line arguments', e1, args : ['first', 'second'])
test('environment variables', e2, env : ['first=val1', 'second=val2'])
test('file arg', find_program('tester.py'), args : files('testfile.txt'))
