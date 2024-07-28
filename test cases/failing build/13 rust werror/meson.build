project('test', default_options: ['werror=true'])
if meson.backend() != 'ninja'
  error('MESON_SKIP_TEST: Rust requires Ninja backend')
endif
if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST: Rust not found')
endif
executable('prog', 'test.rs')
