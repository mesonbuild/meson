project('options', 'c')

# Test passing c_args and c_link_args options from the command line.
assert(get_option('c_args') == ['-funroll-loops'],
       'Incorrect value for c_args option.')
assert(get_option('c_link_args') == ['-random_linker_option'],
       'Incorrect value for c_link_args option.')
