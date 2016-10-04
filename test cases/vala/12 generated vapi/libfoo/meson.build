libfoo_sources = [
  'foo.c',
  'foo.h',
]

libfoo_deps = [
  dependency('gobject-2.0')
]

libfoo = shared_library('foo', libfoo_sources,
  dependencies: libfoo_deps,
  install: true,
)

libfoo_api_ver = '1.0'

libfoo_gir = gnome.generate_gir(libfoo,
  sources: libfoo_sources,
  namespace: 'Foo',
  nsversion: libfoo_api_ver,
  packages: 'gobject-2.0',
  symbol_prefix: 'foo',
  extra_args: [
    '--c-include=foo.h',
  ],
)

libfoo_vapi = gnome.generate_vapi('foo-' + libfoo_api_ver,
  sources: libfoo_gir[0],
  install: true,
)

libfoo_dep = declare_dependency(
  link_with: libfoo,
  include_directories: include_directories('.'),
)
