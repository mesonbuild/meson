project('staticprog', 'c')

rustc = find_program('rustc')
add_languages('rust')

libstd_rust = dependency('std-rust', required: false)

librust = static_library(
  'rust',
  'librust.rs',
  dependencies: libstd_rust,
  rust_crate_type: 'object')

if libstd_rust.found()
  e = executable('c-program', 'prog.c',
    link_with: librust,
    install : true
  )
  test('rusttest', e)
else
  # Requires a discoverable std library, most likely via pkg-config,
  # but there is no common standard so make it optional for now.
  error('MESON_SKIP_TEST: libstd-rust dependency not found')
endif
