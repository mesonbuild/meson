subdir('static')

incfoo = include_directories('.')

# Even if libfoo contains libstatic, it still dynamically link to libshared
# linked by libstatic. This tests that lib/static/shared gets added to PATH
# when an executable links to libfoo.
libfoo = library('foo', 'foo.c', link_whole: libstatic)
