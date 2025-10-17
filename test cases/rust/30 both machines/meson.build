project(
  'testproj',
  'rust',
  version : '0.1',
  meson_version : '>= 1.9.0',
  default_options : ['rust_std=2021'],
)

lib_host = static_library(
  'lib',
  'lib.rs',
  rust_abi: 'rust'
)

lib_build = static_library(
  'lib+build',
  'lib.rs',
  rust_abi: 'rust',
  native: true,
)

exe_host = executable(
  'test-host',
  'test.rs',
  link_with: lib_host,
)

exe_build = executable(
  'test-build',
  'test.rs',
  link_with: lib_build,
  native: true,
)

test('host', exe_host)
test('build', exe_build)
