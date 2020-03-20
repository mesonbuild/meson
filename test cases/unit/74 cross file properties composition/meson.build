project('cross/native property composition')

expected = get_option('expected_val')
actual = meson.get_cross_property('my_args')

assert(expected == actual,
         'my_args should have been @0@, but was @1@!'.format(expected, actual))
