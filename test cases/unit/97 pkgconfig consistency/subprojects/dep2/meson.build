project('dep2')

# It has been overriden, ensure we don't pick the one from pkgconfig
d = dependency('hidden-dep2')
assert(d.type_name() == 'internal')

meson.override_dependency('dep2', declare_dependency(dependencies: d))
