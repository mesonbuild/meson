project('subproject', 'c',
  default_options: {'c_std': 'c11'})

assert(get_option('c_std') == 'c11')

if get_option('opt')
  error('option set when it should be unset.')
endif
