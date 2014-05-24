project('gobject-introspection', 'c')

glib = dependency('glib-2.0')
gobj = dependency('gobject-2.0')

libsources = ['golib.c', 'golib.h']

exe = executable('goprog', libsources, 'prog.c',
deps : [glib, gobj])

test('gobjtest', exe)
