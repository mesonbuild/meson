project('vapi-test', ['c', 'vala'])

if host_machine.system() == 'cygwin'
  error('MESON_SKIP_TEST Does not work with the Vala currently packaged in cygwin')
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
