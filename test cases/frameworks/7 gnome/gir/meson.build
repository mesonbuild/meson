subdir('dep1')

libsources = ['meson-sample.c', 'meson-sample.h']

girlib = shared_library(
  'gir_lib',
  sources : libsources,
  dependencies : [gobj, dep1_dep],
  install : true
)

girexe = executable(
  'girprog',
  sources : 'prog.c',
  dependencies : [glib, gobj, gir, dep1_dep],
  link_with : girlib
)

fake_dep = dependency('no-way-this-exists', required: false)

gnome.generate_gir(
  girlib,
  sources : libsources,
  nsversion : '1.0',
  namespace : 'Meson',
  symbol_prefix : 'meson',
  identifier_prefix : 'Meson',
  includes : ['GObject-2.0', 'MesonDep1-1.0'],
  # dep1_dep pulls in dep2_dep for us
  dependencies : [fake_dep, dep1_dep],
  install : true
)

test('gobject introspection/c', girexe)
gir_paths = ':'.join([girlib.outdir(), dep1lib.outdir(), dep2lib.outdir()])
envdata = environment()
envdata.append('GI_TYPELIB_PATH', gir_paths, separator : ':')
envdata.append('LD_LIBRARY_PATH', gir_paths)
test('gobject introspection/py', find_program('prog.py'),
     env : envdata)
