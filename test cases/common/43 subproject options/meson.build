project('suboptions', default_options: {'c_args': ['-O']})

subproject('subproject')

if not get_option('opt')
  error('option unset when it should be set')
endif
