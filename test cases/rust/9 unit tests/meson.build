project('rust unit tests', 'rust')

t = executable(
  'rust_test',
  ['test.rs'],
  rust_args : ['--test'],
)

test(
  'rust test (should fail)',
  t,
  protocol : 'rust',
  suite : ['foo'],
  should_fail : true,
)

test(
  'rust test (should pass)',
  t,
  args : ['--skip', 'test_add_intentional_fail'],
  protocol : 'rust',
  suite : ['foo'],
)


test(
  'rust test (should skip)',
  t,
  args : ['--skip', 'test_add'],
  protocol : 'rust',
  suite : ['foo'],
)
