
acme_sources = [
  'acme-demo.c'
]

acme_headers = [
  'acme-demo.h'
]

glib_min_version = '>= 2.36.0'
gobject_dep = dependency('gobject-2.0', version: glib_min_version)

acme = static_library(
  'acme',
  sources: acme_sources,
  dependencies: [gobject_dep],
)

acme_dep = declare_dependency(
  link_with: acme,
  dependencies: [gobject_dep],
)