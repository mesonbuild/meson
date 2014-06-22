project('giotest', 'vala', 'c')

glib = dependency('glib-2.0')
gobject = dependency('gobject-2.0')
gio = dependency('gio-2.0')

e = executable('gioprog', 'gioprog.vala',
dependencies : [glib, gobject, gio])
test('giotest', e)
