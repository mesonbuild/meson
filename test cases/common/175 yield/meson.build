project('yield_options', 'c')

subproject('sub')

assert(get_option('unshared_option') == 'one', 'Unshared option has wrong value in superproject.')
assert(get_option('shared_option') == 'two', 'Unshared option has wrong value in superproject..')
