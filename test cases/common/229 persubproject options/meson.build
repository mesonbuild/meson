project('persubproject options', 'c', 'cpp',
  default_options : [
    'default_library=both',
    'c_args=-DPARENT',
    'cpp_std=c++98'
  ]
)

assert(get_option('default_library') == 'both', 'Parent default_library should be "both"')
assert(get_option('c_args') == ['-DPARENT'], 'Parent c_args are wrong')

# Check it build both by calling a method only both_libraries target implement
lib = library('lib1', 'foo.c')
lib.get_static_lib()

sub1 = subproject('sub1')
sub2 = subproject('sub2',
  default_options : [
    'default_library=static',
    'c_args=-DSUB2_FROM_PARENT',
  ]
)

test('mixing-cpp-version', executable('test1', 'main.cpp', link_with : sub2.get_variable('libcpp11')))
