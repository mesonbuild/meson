project('version compare', meson_version: '>= 0.1')

if meson.version().version_compare('>= 9999')
  error('This should not be executed')
elif meson.version().version_compare('>= 0.55') and false
  error('This should not be executed')
elif not meson.version().version_compare('>= 0.55')
  error('This should not be executed')
elif meson.version().version_compare('>= 0.55')
  # This should not produce a warning even when using a function not available
  # in Meson 0.1.
  foo_dep = declare_dependency()
  meson.override_dependency('foo', foo_dep)
endif

# This should not produce a warning even when using a function not available in
# Meson 0.1.
lib_suffix = meson.version().version_compare('>=1.12.0') ? default() : []

# This will error out if elif cause did not enter
assert(foo_dep.found(), 'meson.version_compare did not work')

subproject('foo')
