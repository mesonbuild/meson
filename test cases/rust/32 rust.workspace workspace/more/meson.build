more_pkg = cargo_ws.package('more')

assert(more_pkg.name() == 'more')
assert(more_pkg.features() == ['default'])
assert(more_pkg.all_features() == ['default'])

l = static_library('more', 'src/lib.rs')
more_dep = declare_dependency(link_with: l)
