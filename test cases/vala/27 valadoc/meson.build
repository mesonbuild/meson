project('valadoc-test', ['c', 'vala'])

valadoc = find_program('valadoc', required: false)
if not valadoc.found()
  error('MESON_SKIP_TEST valadoc not found.')
endif

gnome = import('gnome')

frob_valadoc = gnome.valadoc(
  sources: [ 'frob.vala' ],
  package_name: 'frob',
  package_version: '0.1',
  packages: [ 'gobject-2.0' ],
  doclet: 'html',
  install: true,
)
