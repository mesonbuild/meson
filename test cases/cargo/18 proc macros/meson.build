project('cargo proc macros', 'rust')

rust = import('unstable-rust')

sub1  = rust.subproject('sub1')

exe1 = executable(
  'proc_macro',
  'proc_macro.rs',
  dependencies : sub1.get_variable('dep')
)
test('proc_macro', exe1)