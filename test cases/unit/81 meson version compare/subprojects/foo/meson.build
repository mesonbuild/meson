project('foo', meson_version: '>= 0.1')

if meson.version().version_compare('>= 0.55')
  # This should not produce a warning even when using a function not available
  # in Meson 0.1.
  foo_dep = declare_dependency()
  meson.override_dependency('foo2', foo_dep)
endif
