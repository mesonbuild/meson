project('cargo nested workspace')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST Rust not present, required for Cargo subprojects')
endif

cargo = import('rust').workspace()
