subdir('dep1')

libsources = ['meson-sample.c', 'meson-sample.h']
lib2sources = ['meson-sample2.c', 'meson-sample2.h']
pythonsources = ['meson-python-sample.c', 'meson-python-sample.h']

gen_source = custom_target(
  'meson_sample3.h',
  input : 'meson-sample.h',
  output : 'meson-sample3.h',
  command : [find_program('copy.py'), '@INPUT@', '@OUTPUT@'],
  build_by_default : false,  # this will force a race condition if one exists
)

girlib = shared_library(
  'gir_lib',
  sources : libsources,
  c_args: '-DMESON_TEST_2',
  dependencies : [gobj, dep1_dep],
  install : true
)

girlib2 = shared_library(
  'gir_lib2',
  sources : lib2sources,
  dependencies : [gobj],
  install : true
)

if get_option('b_sanitize') == 'none'
  py3_dep = py3.dependency(embed: true)
else
  warning('Python 3 test not supported with b_sanitize')
  py3_dep = disabler()
endif

if py3_dep.found()
  pythongirlib = shared_library(
    'python_gir_lib',
    sources: pythonsources,
    dependencies: [gobj, py3_dep],
    vs_module_defs: 'meson-python-sample.def',
    install: true
  )
endif

girexe = executable(
  'girprog',
  sources : 'prog.c',
  c_args: '-DMESON_TEST_2',
  dependencies : [glib, gobj, gir, dep1_dep],
  link_with : girlib
)

fake_dep = dependency('no-way-this-exists', required: false)

# g-ir-scanner ignores CFLAGS for MSVC
flags_dep_for_msvc = declare_dependency(
  compile_args: ['-DMESON_TEST_2']
)

girs = [girlib, girlib2]
girs_sources = [libsources, lib2sources, gen_source]
# dep1_dep pulls in dep2_dep for us
girs_deps = [fake_dep, dep1_dep, flags_dep_for_msvc]
if py3_dep.found()
  girs += [pythongirlib]
  girs_sources += [pythonsources]
  girs_deps += [py3_dep]
endif

gnome.generate_gir(
  girs,
  sources : girs_sources,
  nsversion : '1.0',
  namespace : 'Meson',
  symbol_prefix : 'meson',
  identifier_prefix : 'Meson',
  includes : ['GObject-2.0', 'MesonDep1-1.0'],
  dependencies : girs_deps,
  doc_format: 'gtk-doc-markdown',
  install : true,
  build_by_default : true,
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
