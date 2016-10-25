project('valatest', 'c', 'vala')

glib = dependency('glib-2.0')
gobject = dependency('gobject-2.0')

library('foo-1.0', 'foo.vala',
        vala_header: 'foo.h',
        vala_vapi: 'foo.vapi',
        dependencies: [glib, gobject])
