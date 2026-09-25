# "shared" is a normal dependency of "app" (host machine) and a dependency of
# "tool", which is only reachable as a build-dependency (build machine).  It is
# therefore configured for both machines.
shared_host = cargo.package('shared')
host_lib = shared_host.library()
shared_host.override_dependency(declare_dependency(
  link_with: host_lib,
  variables: {'crate': 'shared'},
))
assert(host_lib.name() == 'shared+0_1')

if meson.is_cross_build()
  # The two copies must be distinct targets, told apart by the +build suffix.
  shared_build = cargo.package('shared', native: true)
  build_lib = shared_build.library()
  shared_build.override_dependency(declare_dependency(
    link_with: build_lib,
    variables: {'crate': 'shared'},
  ))
  assert(build_lib.name() == 'shared+0_1+build')
else
  # Meson folds the build machine into the host machine, so one target serves
  # both: asking for the build-machine configuration must return the host one
  # rather than fail.
  cargo.package('shared', native: true)
endif
