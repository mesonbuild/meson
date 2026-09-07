testutil_pkg = cargo.package('testutil')

# testutil does not have dev-dependencies, so it does not need them to be resolved.
assert(not is_disabler(testutil_pkg.dependencies(dev_dependencies: true)))
testutil_pkg.override_dependency(declare_dependency(
  link_with: testutil_pkg.library(),
  variables: {'crate': 'testutil'},
))
