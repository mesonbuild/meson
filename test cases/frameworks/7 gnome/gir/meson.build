libsources = ['meson-sample.c', 'meson-sample.h']

girlib = shared_library(
  'girlib',
  sources : libsources,
  dependencies : gobj,
  install : true
)

girexe = executable(
  'girprog',
  sources : 'prog.c',
  dependencies : [glib, gobj, gir],
  link_with : girlib
)

fake_dep = dependency('no-way-this-exists', required: false)

gnome.generate_gir(
  girlib,
  sources : libsources,
  nsversion : '1.0',
  namespace : 'Meson',
  symbol_prefix : 'meson_',
  identifier_prefix : 'Meson',
  includes : ['GObject-2.0'],
  dependencies : [fake_dep],
  install : true
)

test('gobject introspection/c', girexe)
test('gobject introspection/py', find_program('prog.py'),
     env : ['GI_TYPELIB_PATH=' + girlib.outdir(), 
            'LD_LIBRARY_PATH=' + girlib.outdir(),
     ])
