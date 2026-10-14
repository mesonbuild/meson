mylib_pkg = cargo.package('mylib')

# The "extra" feature is only requested by testutil, which is reachable from
# [dev-dependencies].  Like "cargo test", enabling dev-dependencies unifies it
# into the ordinary build of mylib.
assert(mylib_pkg.features() == ['default', 'extra'])

# The dev-dependencies of a package that is not an entry point are not
# resolved, so a test that needs them is disabled.
assert(is_disabler(mylib_pkg.dependencies(dev_dependencies: true)))

mylib_pkg.override_dependency(declare_dependency(
  link_with: mylib_pkg.library(),
  variables: {'crate': 'mylib'},
))
