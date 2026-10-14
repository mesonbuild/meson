app_pkg = cargo.package('app')

# Requesting "tool" as an extra member must not add it to the normal
# dependency set of the package that declares it as a build-dependency.
crates = []
foreach d : app_pkg.dependencies()
  crates += d.get_variable('crate', default_value: 'unknown')
endforeach
assert(crates == ['shared'])

test('app', app_pkg.executable())
