project('freestanding Rust static libraries', 'c', 'rust',
  default_options: ['rust_panic=abort'])

rust_source = get_option('b_freestanding') ? 'freestanding.rs' : 'hosted.rs'

rust_lib = static_library(
  'rust',
  rust_source,
  rust_abi : 'c',
)

exe = executable('prog', 'main.c', link_with : rust_lib)
test('rust', exe)
