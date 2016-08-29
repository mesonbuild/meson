project('suboptions', 'c')

subproject('subproject')

if not get_option('opt')
  error('option unset when it should be set')
endif

subproject('subproject1', options: 'opt1=true')

if not get_option('opt1')
  error('option unset when it should be set')
endif
