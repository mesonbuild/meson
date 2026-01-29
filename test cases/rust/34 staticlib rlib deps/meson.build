project('staticlib rlib deps', 'c', 'rust', meson_version: '>=1.3.0')

# This rlib is a dependency of the staticlib below.
# When linking the C executable with the staticlib, the rlib should NOT
# appear in the link command because it's already compiled into the staticlib.
lib = static_library('lib', 'lib.rs', rust_abi: 'rust')

staticlib = static_library('staticlib', 'staticlib.rs',
  rust_abi: 'c',
  link_whole: lib,
)

exe = executable('main', 'main.c', link_with: staticlib)
test('main', exe)
