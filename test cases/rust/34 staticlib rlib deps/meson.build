project('staticlib rlib deps', 'c', 'rust', meson_version: '>=1.3.0')

lib = static_library('lib', 'lib.rs', rust_abi: 'rust')

staticlib = static_library('staticlib', 'staticlib.rs',
  rust_abi: 'c',
  link_whole: lib,
)

exe = executable('main', 'main.c', link_with: staticlib)
test('main', exe)
