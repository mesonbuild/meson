project('testsetups', 'c')

vg = find_program('valgrind')

# This is only set when running under Valgrind test setup.
env = environment()
env.set('TEST_ENV', '1')

add_test_setup('valgrind',
  exe_wrapper : [vg, '--error-exitcode=1', '--leak-check=full'],
  timeout_multiplier : 100,
  env : env)

buggy = executable('buggy', 'buggy.c', 'impl.c')
test('Test buggy', buggy)

envcheck = find_program('envcheck.py')
test('test-env', envcheck)

add_test_setup('empty')
add_test_setup('onlyenv', env : env)
add_test_setup('onlyenv2', env : 'TEST_ENV=1')
add_test_setup('onlyenv3', env : ['TEST_ENV=1'])
add_test_setup('wrapper', exe_wrapper : [vg, '--error-exitcode=1'])
add_test_setup('timeout', timeout_multiplier : 20)
