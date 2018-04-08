project('acme', 'c', version : '1.0.0')

gtkdoc = find_program('gtkdoc-mkhtml', required : false)
if not gtkdoc.found()
  error('MESON_SKIP_TEST gtkdoc-mkhtml not found.')
endif

gnome = import('gnome')

src_inc = include_directories('src')

subdir('src')
subdir('doc')
