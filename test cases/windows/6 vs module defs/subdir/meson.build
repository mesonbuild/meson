shlib = shared_library('somedll', 'somedll.c', vs_module_defs : 'somedll.def')

# These don't need to be built, we're just testing the parser
shared_library('some_unusable_dll', 'somedll.c', vs_module_defs : [],
  build_by_default : false)
shared_library('some_other_dll', 'somedll.c', vs_module_defs : ['somedll.def'],
  build_by_default : false)
