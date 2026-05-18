project('cargo-toml-error', 'c')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojets')
endif

# This should trigger a CargoTomlError with proper location info
foo_dep = dependency('foo-0')
