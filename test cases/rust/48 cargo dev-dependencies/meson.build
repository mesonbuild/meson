project('cargo dev-dependencies', 'rust', meson_version: '>= 1.13')

rust = import('rust')
cargo = rust.workspace(dev_dependencies: true)

assert(cargo.packages() == ['app', 'mylib', 'testutil'])

subdir('mylib')
subdir('testutil')

pkg = cargo.package()

# A dev-dependency must not become an ordinary dependency of the package.
normal = []
foreach d : pkg.dependencies()
  normal += d.get_variable('crate', default_value: 'unknown')
endforeach
assert(normal == ['mylib'])

dev_only = []
foreach d : pkg.dependencies(dependencies: false, dev_dependencies: true)
  dev_only += d.get_variable('crate', default_value: 'unknown')
endforeach
assert(dev_only == ['testutil'])

both = []
foreach d : pkg.dependencies(dev_dependencies: true)
  both += d.get_variable('crate', default_value: 'unknown')
endforeach
assert(both == ['mylib', 'testutil'])

lib = pkg.library()
rust.test('app-test', lib,
  dependencies: pkg.dependencies(dependencies: false, dev_dependencies: true),
)
