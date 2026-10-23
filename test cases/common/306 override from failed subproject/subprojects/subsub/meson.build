project('subsub', 'c')

lib = static_library('sub', 'sub.c')
meson.override_dependency('subsub', declare_dependency(link_with : lib, include_directories : '.'))

# The backend must process all of subsub, not just the dependencies
# of targets defined in other subprojects.
install_data('a.txt')
