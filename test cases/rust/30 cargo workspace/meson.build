project('cargo workspace', 'c', 'rust')

foo_rs = dependency('foo-1-rs')
e = executable('test-foo-1-rs', 'test_foo_1.rs',
  dependencies: [foo_rs],
)
test('test-foo-1-rs', e)

foo_cdylib = dependency('foo-1')
e = executable('test-foo-1-cdylib', 'test_foo_1.c',
  dependencies: [foo_cdylib],
)
test('test-foo-1-rs', e)
