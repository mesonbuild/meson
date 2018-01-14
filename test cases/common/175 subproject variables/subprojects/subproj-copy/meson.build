project('subproj-copy', 'c')
inc = include_directories('include-copy')
lib = shared_library('subprojlib-copy', 'subprojlib-copy.c', include_directories : inc, c_args : '-DBUILDING_SUB=1')
depvar = declare_dependency(include_directories : inc, link_with : lib)
