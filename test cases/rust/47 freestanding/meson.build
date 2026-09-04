project('freestanding Rust static libraries', 'c', 'rust')

rust_source = get_option('b_freestanding') ? 'freestanding.rs' : 'hosted.rs'

rust_lib = static_library(
  'rust',
  rust_source,
  rust_abi : 'c',
  rust_args : ['-C', 'panic=abort'],
)

exe = executable('prog', 'main.c', link_with : rust_lib)
test('rust', exe)
