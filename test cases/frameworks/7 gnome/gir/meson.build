subdir('dep1')

libsources = ['meson-sample.c', 'meson-sample.h']
lib2sources = ['meson-sample2.c', 'meson-sample2.h']

girlib = shared_library(
  'gir_lib',
  sources : libsources,
  dependencies : [gobj, dep1_dep],
  install : true
)

girlib2 = shared_library(
  'gir_lib2',
  sources : lib2sources,
  dependencies : [gobj],
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
  girlib, girlib2,
  sources : libsources + lib2sources,
  nsversion : '1.0',
  namespace : 'Meson',
  symbol_prefix : 'meson',
  identifier_prefix : 'Meson',
  includes : ['GObject-2.0', 'MesonDep1-1.0'],
  # dep1_dep pulls in dep2_dep for us
  dependencies : [[fake_dep, dep1_dep]],
  install : true,
  build_by_default : true,
  # Test that unknown kwargs do not crash the parser.
  # Unknown kwargs will eventually become a hard error.
  # Once that happens remove this.
  unknown_kwarg : true,
)

test('gobject introspection/c', girexe)
gir_paths = ':'.join([girlib.outdir(), dep1lib.outdir(), dep2lib.outdir(), dep3lib.outdir()])
envdata = environment()
envdata.append('GI_TYPELIB_PATH', gir_paths, separator : ':')
envdata.append('LD_LIBRARY_PATH', gir_paths)
if ['windows', 'cygwin'].contains(host_machine.system())
  envdata.append('PATH', gir_paths)
endif
test('gobject introspection/py', find_program('prog.py'),
     env : envdata)
