project('gobject-introspection', 'c')

gnome = import('gnome')
gio = dependency('gio-2.0')
glib = dependency('glib-2.0')
gobj = dependency('gobject-2.0')
gir = dependency('gobject-introspection-1.0')
gmod = dependency('gmodule-2.0')

myres = gnome.compile_resources('myresources', 'myresource.gresource.xml',
source_dir : 'data',
c_name : 'myres')

resexe = executable('resprog', 'main.c', myres,
dependencies : gio)
test('resource test', resexe)

libsources = ['golib.c', 'golib.h']

girexe = executable('girprog', libsources, 'prog.c',
dependencies : [glib, gobj, gir, gmod])

gnome.generate_gir(girexe,
sources : libsources,
nsversion : '1.0',
namespace : 'Meson',
install : true,
install_dir : 'typelibdir',
)

test('gobject introspection', girexe)

gnome.compile_schemas()
install_data('com.github.meson.gschema.xml',
install_dir : 'share/glib-2.0/schemas')

schemaexe = executable('schemaprog', 'schemaprog.c',
dependencies : gio)
test('schema test', schemaexe)
