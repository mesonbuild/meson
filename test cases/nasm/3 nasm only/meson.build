project('nasm only')

if not add_languages('nasm', required: false)
  error('MESON_SKIP_TEST: nasm not found')
endif

sources = files('dummy.asm')

dummy = library(
    'dummy',
    sources,
    vs_module_defs: 'dummy.def',
)
