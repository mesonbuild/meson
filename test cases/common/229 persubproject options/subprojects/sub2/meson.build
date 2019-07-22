project('sub2', 'c', 'cpp',
  default_options : [
    'default_library=shared',
    'c_args=-DSUB2',
    'cpp_std=c++11'
  ]
)

assert(get_option('default_library') == 'static', 'Parent should override default_library')
assert(get_option('c_args') == ['-DSUB2_FROM_PARENT'], 'Parent should override c_args')

# If it doesn't build only a static library, it would make target name clash.
library('lib1', 'foo.c')
shared_library('lib1', 'foo.c')

# Parent project is c++98 but this one uses c++11 to build.
libcpp11 = library('lib2', 'foo.cpp')
