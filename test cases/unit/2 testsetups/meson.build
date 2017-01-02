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

