project('test', 'c')

# Built-in options
assert(get_option('default_library') == 'both')
assert(get_option('datadir') == 'my_datadir')

# Project options
assert(get_option('opt1') == true)
assert(get_option('opt2') == true)
assert(get_option('opt3') == 1)

# Per machine built-in options
assert(get_option('pkg_config_path') == ['/cross'])
assert(get_option('build.pkg_config_path') == ['/native'])

# Per machine compiler options
assert(get_option('c_args') == ['-DCROSS'])
assert(get_option('build.c_args') == ['-DNATIVE'])

subproject('sub')
