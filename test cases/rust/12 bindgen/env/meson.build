# SPDX-license-identifer: Apache-2.0

gen_env = rust.bindgen(
  input : 'header.h',
  output : 'header.rs',
  env : {'BINDGEN_EXTRA_CLANG_ARGS' : '-DEXPOSE_API'},
  include_directories : inc,
)

f_env = configure_file(
  input : '../src/main.rs',
  output : 'main.rs',
  copy : true,
)

rust_bin_env = executable(
  'rust_bin_env',
  [f_env, gen_env],
  link_with : c_lib,
)

test('generate with custom environment variables', rust_bin_env)
