project('sub2', 'c', default_options : ['default_library=shared'])

assert(get_option('default_library') == 'static', 'Parent should override default_library')

# If it doesn't build only a static library, it would make target name clash.
library('lib1', 'foo.c')
shared_library('lib1', 'foo.c')
