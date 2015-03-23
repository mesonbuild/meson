
libsources = ['golib.c', 'golib.h']

girexe = executable('girprog', libsources, 'prog.c',
dependencies : [glib, gobj, gir, gmod])

gnome.generate_gir(girexe,
sources : libsources,
nsversion : '1.0',
namespace : 'Meson',
includes : ['GObject-2.0', 'Gio-2.0'],
install : true
)

test('gobject introspection', girexe)
