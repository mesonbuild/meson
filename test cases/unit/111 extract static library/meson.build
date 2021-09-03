project('extract archives', 'c')

glib_dep = dependency('glib-2.0',
  static: true,
  required: false,
)

if not glib_dep.found()
  error('MESON_SKIP_TEST glib static library is needed')
endif

both_libraries('glib-wrapper',
  dependencies: glib_dep.as_link_whole(),
  install: true,
)
