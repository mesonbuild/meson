project('test features', 'c')

e1 = executable('cmd_args', 'cmd_args.c')
e2 = executable('envvars', 'envvars.c')
e3 = executable('env2vars', 'env2vars.c')

env = environment()
env.set('first', 'val1')
env.set('second', 'val2')
env.set('third', 'val3', 'and_more', separator: ':')
env.append('PATH', 'fakepath', separator: ':')

# Make sure environment objects are copied on assignment and we can
# change the copy without affecting the original environment object.
env2 = env
env2.set('first', 'something-else')

test('command line arguments', e1, args : ['first', 'second'])
test('environment variables', e2, env : env)
test('environment variables 2', e3, env : env2)
test('file arg', find_program('tester.py'), args : files('testfile.txt'))
