mylib_pkg = cargo.package('mylib')

# The "extra" feature is only requested by testutil, which is reachable from
# [dev-dependencies].  Like "cargo test", enabling dev-dependencies unifies it
# into the ordinary build of mylib.
assert(mylib_pkg.features() == ['default', 'extra'])

mylib_pkg.override_dependency(declare_dependency(
  link_with: mylib_pkg.library(),
  variables: {'crate': 'mylib'},
))
