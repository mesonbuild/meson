project('rust separate rlib', 'rust', meson_version: '>= 1.13')

cargo = import('rust').workspace()
assert(cargo.packages() == ['mylib'])

pkg = cargo.package()
rlib = pkg.library()
pkg.override_dependency(declare_dependency(link_with: rlib))
