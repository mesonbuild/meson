project('exclude-outside-test', 'c')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojets')
endif

rust = import('rust')
cargo_ws = rust.workspace()
