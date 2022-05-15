project('normalize option name',
  default_options: ['default-library=static'])

assert(get_option('default-library') == 'static')
assert(get_option('default_library') == 'static')
assert(get_option('warning-level') == '3')
assert(get_option('warning_level') == '3')
assert(get_option('foo-bar'))
assert(get_option('foo_bar'))
