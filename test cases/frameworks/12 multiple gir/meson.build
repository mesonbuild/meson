project('multiple-gobject-introspection', 'c')

gir = find_program('g-ir-scanner', required: false)
if not gir.found()
  error('MESON_SKIP_TEST g-ir-scanner not found.')
endif

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST GIR seems to be broken in Cygwin and no-one knows how to fix it. Thus we have to disable this.')
endif

gnome = import('gnome')
gobj = dependency('gobject-2.0')

subdir('mesongir')
subdir('gir')
