project('hotdoc', 'c')

hotdoc = find_program('hotdoc', required: false)
if not hotdoc.found()
  error('MESON_SKIP_TEST hotdoc not found.')
endif

subdir('doc')

