
datadir = join_paths(get_option('datadir'), 'doc', 'acme')

gnome.gtkdoc(
  meson.project_name(),
  main_xml: meson.project_name() + '-docs.xml',
  src_dir: [
    src_inc,
  ],
  dependencies: [
    acme_dep,
  ],
  gobject_typesfile: 'acme.types',
  scan_args: [
    '--rebuild-sections',
    '--rebuild-types',
  ],
  mkdb_args: [
    '--output-format=xml',
  ],
  install: true,
  install_dir: datadir,
)
