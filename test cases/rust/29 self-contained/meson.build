project('self-contained', meson_version : '>= 1.3.0')

if not add_languages('c', native : false, required : false)
  error('MESON_SKIP_TEST clang not installed')
endif

if not add_languages('rust', native : false, required : false)
  error('MESON_SKIP_TEST Rust x86_64-unknown-linux-musl target not installed')
endif

if meson.get_compiler('c').find_library('libunwind', required : false).found()
  error('MESON_SKIP_TEST libunwind is installed globally')
endif

lib = static_library('rust', 'lib.rs', rust_abi : 'c')

executable('exe', 'main.c', link_with : lib)
