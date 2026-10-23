project('subsub', 'c')

lib = static_library('sub', 'sub.c')
meson.override_dependency('subsub', declare_dependency(link_with : lib, include_directories : '.'))
