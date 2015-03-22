
libsources = ['golib.c', 'golib.h']

girexe = executable('girprog', libsources, 'prog.c',
dependencies : [glib, gobj, gir, gmod])

gnome.generate_gir(girexe,
sources : libsources,
nsversion : '1.0',
namespace : 'Meson',
install : true
)

test('gobject introspection', girexe)
