project('demo', 'c', 'vala')

gnome = import('gnome', required: false)

if not gnome.found()
  error('MESON_SKIP_TEST: gnome module not supported')
endif

deps = [
  dependency('glib-2.0', version : '>=2.50'),
  dependency('gobject-2.0'),
  dependency('gtk+-3.0'),
]

subdir('subdir')

executable(
  'demo',
  'test.vala',
  resources,
  dependencies: deps,
)
