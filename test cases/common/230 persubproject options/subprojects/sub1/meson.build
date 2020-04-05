project('sub1', 'c')

assert(get_option('default_library') == 'both', 'Should inherit parent project default_library')

# Check it build both by calling a method only both_libraries target implement
lib = library('lib1', 'foo.c')
lib.get_static_lib()
