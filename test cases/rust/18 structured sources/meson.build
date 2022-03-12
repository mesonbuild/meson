project('structured input', 'rust')

foo_mod_rs = configure_file(
  input : 'src/foo.rs.in',
  output : 'mod.rs',
  configuration : {'message' : 'Hello, World!'},
)

conf_file = executable(
  'main_conf_file',
  structured_sources(
    'src/main.rs',
    {'foo' : [foo_mod_rs]},
  ),
)

ct = custom_target(
  'foo.rs',
  output : 'foo.rs',
  command : ['gen.py', '@OUTPUT@'],
)

target = executable(
  'main_custom_target',
  structured_sources(
    ['src/main.rs', ct],
  ),
)

# Should not be coppied
executable(
  'no_copy_target',
  structured_sources(
    ['src2/main-unique.rs'],
    {'foo': 'src2/foo/mod.rs'},
  ),
)

test('no-copy', find_program('no_copy_test.py'), args : meson.current_build_dir())
