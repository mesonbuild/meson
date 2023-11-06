project('cargo subproject', 'c', meson_version : '>= 1.3.0')

foo_dep = dependency('foo-rs')
exe = executable('app', 'main.c',
  dependencies: foo_dep,
)
test('cargo-test', exe)
