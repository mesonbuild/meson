project('multiple files', 'vala', 'c')

glib = dependency('glib-2.0')
gobject = dependency('gobject-2.0')

e = executable('prog', 'main.vala', 'class1.vala', 'class2.vala',
dependencies : [glib, gobject])
test('multiple file test', e)
