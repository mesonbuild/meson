project('glib compile resource', 'c')

gnome = import('gnome')
gio = dependency('gio-2.0')

myres = gnome.compile_resources('myresources', 'myresource.gresource.xml',
source_dir : 'data',
c_name : 'myres')

exe = executable('resprog', 'main.c', myres,
dependencies : gio)
test('resource test', exe)
