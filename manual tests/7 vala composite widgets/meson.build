project('composite', 'vala', 'c')
gnome = import('gnome')
deps = [
  dependency('glib-2.0', version : '>=2.38'),
  dependency('gobject-2.0'),
  dependency('gtk+-3.0'),
]
res = gnome.compile_resources(
  'my', 'my-resources.xml',
  source_dir : '.',
)
executable(
  'demo',
  sources : [
    'mywidget.vala',
    res,
  ],
  dependencies : deps,
  vala_args : ['--gresources', res]),
)
