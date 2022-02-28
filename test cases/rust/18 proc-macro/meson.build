project('rust proc-macro', 'rust')

if build_machine.system() != 'linux'
    error('MESON_SKIP_TEST, this test only works on Linux. Patches welcome.')
endif

pm = shared_library(
  'proc_macro_examples',
  'proc.rs',
  rust_crate_type : 'proc-macro',
)

main = executable(
  'main',
  'use.rs',
  link_with : pm
)

test('main_test', main)
