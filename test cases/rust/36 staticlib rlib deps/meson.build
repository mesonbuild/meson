project('staticlib rlib deps', 'c', 'rust', meson_version: '>=1.3.0')

# This rlib is a dependency of the staticlib below.
# When linking the C executable with the staticlib, the rlib should NOT
# appear in the link command because it's already compiled into the staticlib.
lib = static_library('lib', 'lib.rs', rust_abi: 'rust')

staticlib_whole = static_library('staticlib-whole', 'staticlib.rs',
  rust_abi: 'c',
  link_whole: lib,
)

exe = executable('main-whole', 'main.c', link_with: staticlib_whole)
test('main', exe)

exe = executable('main-whole-rs', 'main.rs', link_with: staticlib_whole)
test('main', exe)

staticlib_with = static_library('staticlib-with', 'staticlib.rs',
  rust_abi: 'c',
  link_with: lib,
)

exe = executable('main-with', 'main.c', link_with: staticlib_with)
test('main', exe)

exe = executable('main-with-rs', 'main.rs', link_with: staticlib_with)
test('main', exe)
