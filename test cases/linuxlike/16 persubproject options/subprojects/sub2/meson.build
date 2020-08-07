project('sub2', 'c', 'cpp',
  default_options : [
    'default_library=shared',
    'werror=false',
    'cpp_std=c++11',
  ],
)

assert(get_option('default_library') == 'static', 'Parent should override default_library')
assert(not get_option('werror'))
assert(get_option('cpp_std') == 'c++11')

# If it doesn't build only a static library, it would make target name clash.
library('lib1', 'foo.c')
shared_library('lib1', 'foo.c')

# Parent project is c++98 but this one uses c++11 to build.
libcpp11 = library('lib2', 'foo.cpp')
