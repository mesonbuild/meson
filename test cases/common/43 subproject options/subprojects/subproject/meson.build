project('subproject', 'c',
  default_options: {'c_std': 'c11', 'c_args': ['-O2']})

assert(get_option('c_std') == 'c11')
# could be -O2 as above, or for some cross compilation tests in
# CI it could come from the machine file.  but it's certainly
# not the value in the top-level project.
assert(get_option('c_args') != ['-O'])

if get_option('opt')
  error('option set when it should be unset.')
endif
