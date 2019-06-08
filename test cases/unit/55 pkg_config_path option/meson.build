project('pkg_config_path option')

build = dependency('totally_made_up_dep', native: true, method : 'pkg-config')
host = dependency('totally_made_up_dep', native: false, method : 'pkg-config')

# TODO always test we can do this separately
if meson.is_cross_build()
   assert(build.version() == '4.5.6', 'wrong version for build machine dependency')
else
   assert(host.version() == '1.2.3', 'wrong version for host machine dependency')
endif
assert(host.version() == '1.2.3', 'wrong version for host machine dependency')
