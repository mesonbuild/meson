project('foo', 'c')

libfoo = library('foo', ['foo.c', 'foo.h'])

libfoo_dep = declare_dependency(include_directories: '.', link_with: libfoo)
