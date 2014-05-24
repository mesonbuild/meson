project('gobject-introspection', 'c')

glib = dependency('glib-2.0')
gobj = dependency('gobject-2.0')
gir = dependency('gobject-introspection-1.0')
gmod = dependency('gmodule-2.0')

girscan = find_program('g-ir-scanner')
girc = find_program('g-ir-compiler')

libsources = ['golib.c', 'golib.h']

exe = executable('goprog', libsources, 'prog.c',
deps : [glib, gobj, gir, gmod])

test('gobjtest', exe)

# Let's create Gir data with custom targets to prove that
# Meson's syntax is expressive enough.
r = run_command('pkg-config', '--cflags', 'gobject-introspection-1.0')
custom_gir_args = r.stdout().strip().split()

golibgir = custom_target('golibgir',
  output : 'Meson-1.0.gir',
  input : libsources,
  command : [girscan, '@INPUT@', '--program', exe, custom_gir_args, '--include=GObject-2.0',
  '--namespace=Meson', '--nsversion=1.0', '--output', '@OUTPUT@'],
)

custom_target('golibtypelib',
  output : 'Meson-1.0.typelib',
  command : [girc, golibgir,'--output', '@OUTPUT@'],
  install : true,
  install_dir : 'typelibdir'
)
