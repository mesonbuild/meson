project('workspace exclude test', 'rust', default_options: ['rust_std=2021'])

rust = import('rust')
cargo_ws = rust.workspace()

# 'extra' is excluded from the workspace, so it should NOT appear in packages()
pkgs = cargo_ws.packages()
assert(pkgs == ['exclude_test'], 'excluded member must not be in packages()')

# Trying to access the excluded member via workspace.package() should fail
testcase expect_error('workspace member "extra" not found')
  cargo_ws.package('extra')
endtestcase

# The excluded subproject is still reachable via the standard meson subproject()
extrasp = subproject('extra-0.1-rs')
assert(extrasp.found(), 'excluded subproject should be reachable via subproject()')

# Build the root package
main_pkg = cargo_ws.package()
e = executable('exclude-test', 'src/main.rs',
  dependencies: main_pkg.dependencies(),
  rust_args: main_pkg.rust_args(),
  rust_dependency_map: main_pkg.rust_dependency_map(),
)
test('exclude-test', e)
