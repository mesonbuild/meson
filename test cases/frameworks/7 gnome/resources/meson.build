myres = gnome.compile_resources('myresources', 'myresource.gresource.xml',
source_dir : 'data',
c_name : 'myres')

resexe = executable('resprog', 'main.c', myres,
dependencies : gio)
test('resource test', resexe)
