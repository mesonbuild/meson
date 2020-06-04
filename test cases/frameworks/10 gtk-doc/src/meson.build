gobj = dependency('gobject-2.0')

libbaz = shared_library('baz', 'baz_trivial.c', dependencies: gobj)
incbaz = include_directories('.')

libbaz_dep = declare_dependency(link_with: libbaz,
                                dependencies: gobj,
                                include_directories: incbaz)
