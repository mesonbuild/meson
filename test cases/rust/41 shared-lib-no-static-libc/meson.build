project('shared-lib-no-static-libc', meson_version : '>= 1.3.0')

if not add_languages('c', native : false, required : false)
  error('MESON_SKIP_TEST clang not installed')
endif

if not add_languages('rust', native : false, required : false)
  error('MESON_SKIP_TEST Rust x86_64-unknown-linux-musl target not installed')
endif

rust_lib = static_library('hello', 'lib.rs', rust_abi : 'c')

shared = shared_library('hello_shared', 'shim.c',
  link_whole : rust_lib)

exe = executable('exe', 'main.c',
  link_with : shared)

test('no-embedded-libc', exe)
