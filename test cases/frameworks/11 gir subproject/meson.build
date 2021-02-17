project('gobject-introspection-with-subproject', 'c')

gir = find_program('g-ir-scanner', required: false)
if not gir.found()
  error('MESON_SKIP_TEST g-ir-scanner not found.')
endif

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST GIR seems to be broken in Cygwin and no-one knows how to fix it. Thus we have to disable this.')
endif

python3 = import('python3')
py3 = python3.find_python()
if run_command(py3, '-c', 'import gi;').returncode() != 0
    error('MESON_SKIP_TEST python3-gi not found')
endif

gnome = import('gnome')
gobj = dependency('gobject-2.0')

add_global_arguments('-DMESON_TEST', language : 'c')
meson_gir = dependency('meson-gir', fallback : ['mesongir', 'meson_gir'])

subdir('gir')
