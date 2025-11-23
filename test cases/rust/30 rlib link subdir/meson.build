project(
  'rlib-link-subdir',
  ['c', 'rust'],
  default_options: ['rust_std=2021']
)

subdir('cdep')
f_sys = static_library(
  'f_sys',
  'f-sys.rs',
  link_with: cdep,
  rust_abi: 'rust',
)

exe = executable(
  'main',
  'main.rs',
  link_with: f_sys,
)

test('basic', exe)
