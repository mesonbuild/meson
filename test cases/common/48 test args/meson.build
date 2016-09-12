project('test features', 'c')

e1 = executable('cmd_args', 'cmd_args.c')
e2 = executable('envvars', 'envvars.c')

env = environment()
env.set('first', 'val1')
env.set('second', 'val2')
env.set('third', 'val3', 'and_more', separator: ':')
env.append('PATH', 'fakepath', separator: ':')

test('command line arguments', e1, args : ['first', 'second'])
test('environment variables', e2, env : env)
test('file arg', find_program('tester.py'), args : files('testfile.txt'))
