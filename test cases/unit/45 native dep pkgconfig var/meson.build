project('native dep pkgconfig test')

if get_option('start_native')
  dep_native = dependency('dep_tester', native: true, method: 'pkg-config')
  dep_cross = dependency('dep_tester', native: false, method: 'pkg-config')
else
  dep_cross = dependency('dep_tester', native: false, method: 'pkg-config')
  dep_native = dependency('dep_tester', native: true, method: 'pkg-config')
endif

dep_type = dep_native.get_pkgconfig_variable('dep_type')
assert(dep_type == 'native', 'Expected native')

dep_type = dep_cross.get_pkgconfig_variable('dep_type')
assert(dep_type == 'cross', 'Expected cross')

pkgconfig = find_program('pkgconfig', native: false)
pkg_config = find_program('pkg-config', native: false)
assert(pkgconfig.full_path() == pkg_config.full_path())
