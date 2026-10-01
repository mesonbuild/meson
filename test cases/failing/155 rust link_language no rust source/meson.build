project('rust link language without rust sources', 'c')

if not add_languages('rust', required: false)
  error('MESON_SKIP_TEST test requires rust compiler')
endif

executable('hello', 'hello.c', link_language: 'rust')
