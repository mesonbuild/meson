project('structured input', 'rust')

foo_mod_rs = configure_file(
  input : 'src/foo.rs.in',
  output : 'mod.rs',
  configuration : {'message' : 'Hello, World!'},
)

conf_file = executable(
  'main_conf_file',
  {
    '' : 'src/main.rs',
    'foo' : [foo_mod_rs],
  },
)

ct = custom_target(
  'foo.rs',
  output : 'foo.rs',
  command : ['gen.py', '@OUTPUT@'],
)

target = executable(
  'main_custom_target',
  {
    '' : ['src/main.rs', ct],
  },
)
