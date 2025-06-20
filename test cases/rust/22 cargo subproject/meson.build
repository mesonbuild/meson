project('cargo subproject', 'c')

foo_dep = dependency('foo-0-cdylib')
exe = executable('app', 'main.c',
  dependencies: foo_dep,
)
test('cargo-test', exe)
