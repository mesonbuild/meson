project('foob', 'c',
  default_options : ['defopoverride=s_defopt', # This should be overridden.
                     'fromcmdline=s_defopt']   # This should get the value set in command line.
  )

assert(get_option('fromcmdline') == 's_cmdline', 'Default option defined in cmd line is incorrect: ' + get_option('fromcmdline'))
assert(get_option('defopoverride') == 's_defopt', 'Default option without cmd line override is incorrect: ' + get_option('defopoverride'))
assert(get_option('fromoptfile') == 's_optfile', 'Default value from option file is incorrect: ' + get_option('fromoptfile'))

