project('test', default_options: ['werror=true'])
if meson.backend().startswith('vs')
  error('MESON_SKIP_TEST: VS backend does not recognise NASM yet')
endif
if not add_languages('nasm', required: false)
  error('MESON_SKIP_TEST: nasm not found')
endif
executable('prog', 'test.asm')
