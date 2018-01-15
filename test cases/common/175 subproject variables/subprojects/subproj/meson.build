project('subproj', 'c')
inc = include_directories('include')
lib = shared_library('subprojlib', 'subprojlib.c', include_directories : inc, c_args : '-DBUILDING_SUB=1')
depvar = declare_dependency(include_directories : inc, link_with : lib)
