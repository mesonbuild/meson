project('persubproject options', 'c',
  default_options : ['default_library=both',
                     'werror=true',
                     'warning_level=3'])

assert(get_option('default_library') == 'both', 'Parent default_library should be "both"')
assert(get_option('werror'))
assert(get_option('warning_level') == '3')

# Check it build both by calling a method only both_libraries target implement
lib = library('lib1', 'foo.c')
lib.get_static_lib()

subproject('sub1')
subproject('sub2', default_options : ['default_library=static'])
