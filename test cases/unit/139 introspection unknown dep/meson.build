project('t', 'c')
logind = get_option('logind')
enable_logind = (logind != 'none')
if enable_logind
  logind_dep = dependency(logind, version: '>= 209')
endif
