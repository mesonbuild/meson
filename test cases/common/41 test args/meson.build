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

# https://github.com/mesonbuild/meson/issues/2211#issuecomment-327741571
env_array = ['MESONTESTING=picklerror']
testfile = files('testfile.txt')
testerpy = find_program('tester.py')
test('file arg', testerpy, args : testfile, env : [env_array, 'TEST_LIST_FLATTENING=1'])

copy = find_program('copyfile.py')
tester = executable('tester', 'tester.c')
testfilect = custom_target('testfile',
                           input : testfile,
                           output : 'outfile.txt',
                           build_by_default : true,
                           command : [copy, '@INPUT@', '@OUTPUT@'])
test('custom target arg', tester, args : testfilect, env : env_array)

# https://github.com/mesonbuild/meson/issues/12327
env = environment()
env.append('PATH', 'something')

pathtester = find_program('pathtester.py')

custompathtgt = custom_target('testpathappend',
                              output : 'nothing.txt',
                              build_always : true,
                              command : [pathtester],
                              env : env)

# https://github.com/mesonbuild/meson/issues/3552
wrap = find_program('wrap.py')
test('external program arg', wrap, args : [testerpy, testfile])
