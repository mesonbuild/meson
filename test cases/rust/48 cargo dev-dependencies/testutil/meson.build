testutil_pkg = cargo.package('testutil')
testutil_pkg.override_dependency(declare_dependency(
  link_with: testutil_pkg.library(),
  variables: {'crate': 'testutil'},
))
