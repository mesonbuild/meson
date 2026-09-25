project('cargo dev-dependency cycle', 'rust', meson_version: '>= 1.13')

rust = import('rust')
cargo = rust.workspace(dev_dependencies: true)

assert(cargo.packages() == ['a', 'b'])

# a dev-depends on b and b depends on a.  There is no cycle between Meson
# targets: a's library does not use b, only a's test executable does.
a_pkg = cargo.package('a')
a_lib = a_pkg.library()
a_pkg.override_dependency(declare_dependency(
  link_with: a_lib,
  variables: {'crate': 'a'},
))

b_pkg = cargo.package('b')
b_pkg.override_dependency(declare_dependency(
  link_with: b_pkg.library(),
  variables: {'crate': 'b'},
))

dev_deps = a_pkg.dependencies(dependencies: false, dev_dependencies: true)
assert(dev_deps.length() == 1)
assert(dev_deps[0].get_variable('crate') == 'b')

rust.test('a-test', a_lib, dependencies: dev_deps)
