more_pkg = cargo_ws.package('more')

assert(more_pkg.name() == 'more')
assert(more_pkg.features() == ['default'])
assert(more_pkg.all_features() == ['default'])

l = static_library('more', 'src/lib.rs',
  rust_args: more_pkg.rust_args(),
  rust_dependency_map: more_pkg.rust_dependency_map(),
)
more_dep = declare_dependency(link_with: l)
meson.override_dependency('more-0.1-rs', more_dep)
