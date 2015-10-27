project('bob', 'c')

boblib = static_library('bob', 'bob.c')
bobinc = include_directories('.')

bob_dep = declare_dependency(link_with : boblib,
  include_directories : bobinc)
