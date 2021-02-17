project('vapi-test', ['c', 'vala'])

if build_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST GIR seems to be broken in Cygwin and no-one knows how to fix it. Thus we have to disable this.')
endif

gnome = import('gnome')
subdir('libfoo')
subdir('libbar')

vapiexe = executable('vapigen-test',
  'main.vala',
  dependencies: [dependency('gobject-2.0'), libfoo_vapi, libbar_vapi],
  install: true,
)

test('vapigen-test', vapiexe)
