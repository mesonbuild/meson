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
