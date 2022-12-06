project('nasm and c together', 'c')

if not add_languages('nasm', required: false)
  error('MESON_SKIP_TEST: nasm not found')
endif

if meson.backend().startswith('vs')
  error('MESON_SKIP_TEST: VS backend does not recognise NASM yet')
endif

sources = files('dummy.asm', 'hello.c')

hello = executable(
  'hello',
  sources,
)

test('hello', hello)
