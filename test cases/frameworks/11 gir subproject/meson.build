project('gobject-introspection-with-subproject', 'c')

gnome = import('gnome')
gobj = dependency('gobject-2.0')

add_global_arguments('-DMESON_TEST', language : 'c')
meson_gir = dependency('meson-gir', fallback : ['mesongir', 'meson_gir'])

subdir('gir')

