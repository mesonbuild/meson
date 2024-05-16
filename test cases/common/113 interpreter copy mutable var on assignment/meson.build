project('foo', meson_version: '>=1.5')

a = configuration_data()
a.set('HELLO', 1)

b = a

assert(a.has('HELLO'), 'Original config data should be set on a')
assert(b.has('HELLO'), 'Original config data should be set on copy')

configure_file(output : 'b.h', configuration : b)

testcase expect_error('Can not modify object after it has been used.')
  b.set('WORLD', 1)
endtestcase

# A copy of immutable object is mutable. This should print FeatureNew warning
# if meson_version is lower than 1.5.
c = b
c.set('WORLD', 1)

# This should still work, as we didn't use the original above but a copy!
a.set('WORLD', 1)

assert(a.has('WORLD'), 'New config data should have been set')
assert(not b.has('WORLD'), 'New config data set should not affect var copied earlier')

configure_file(output : 'a.h', configuration : a)

env1 = environment()
env1.set('FOO', '1')
env2 = env1
env1.set('BAR', '1')

# FOO should be in env1 and env2
run_command('check_env.py', 'FOO', env: env1, check: true)
run_command('check_env.py', 'FOO', env: env2, check: true)

# BAR should be only in env1
run_command('check_env.py', 'BAR', env: env1, check: true)
assert(run_command('check_env.py', 'BAR', env: env2, check: false).returncode() == 42)

# This should print deprecation warning but still work
env1.set('PLOP', '1')
run_command('check_env.py', 'PLOP', env: env1, check: true)

# A copy of used env should be mutable and not print warning
env3 = env1
env3.set('BAZ', '1')
run_command('check_env.py', 'PLOP', env: env3, check: true)
run_command('check_env.py', 'BAZ', env: env3, check: true)
