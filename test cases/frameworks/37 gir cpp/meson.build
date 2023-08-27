project('gnome module without C', 'cpp')

gi = dependency('gobject-introspection-1.0', required: false)
if not gi.found()
  error('MESON_SKIP_TEST gobject-introspection not found.')
endif

gnome = import('gnome')

lib = library('foo++', 'foo.cpp')
gnome.generate_gir(
  lib,
  sources: ['foo.cpp', 'foo.h'],
  namespace: 'foo',
  nsversion: meson.project_version(),
)
