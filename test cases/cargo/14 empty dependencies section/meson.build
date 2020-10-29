project('cargo lib', 'rust')

rust = import('unstable-rust')
sub = rust.subproject('mylib')

dep = sub.get_variable('dep')

executable(
  'app',
  'app.rs',
  dependencies : dep,
)
