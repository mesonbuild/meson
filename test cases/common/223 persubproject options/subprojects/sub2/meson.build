project('sub2', 'c',
 default_options : ['default_library=shared',
                    'werror=false'])

assert(get_option('default_library') == 'static', 'Parent should override default_library')
assert(not get_option('werror'))

# If it doesn't build only a static library, it would make target name clash.
library('lib1', 'foo.c')
shared_library('lib1', 'foo.c')
