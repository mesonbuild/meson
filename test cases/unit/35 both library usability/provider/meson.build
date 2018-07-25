project('both library provider', 'c')

pkg = import('pkgconfig')

subdir('otherlib')

# Both libraries with a link_whole dependency on an installed static library
l1 = library('whole-installed', 'both.c',
            c_args : ['-DINSTALLED_LIBRARY'],
            link_whole : installed_lib,
            install: true)
pkg.generate(l1)

# Both libraries with a link_whole dependency on a not-installed static library
l2 = library('whole-internal', 'both.c',
            link_whole : internal_lib,
            install: true)
pkg.generate(l2)

# Both libraries with a link_with dependency on an installed static library
l3 = library('with-installed', 'both.c',
            c_args : ['-DINSTALLED_LIBRARY'],
            link_with : installed_lib,
            install: true)
pkg.generate(l3)

# Both libraries with a link_with dependency on a not-installed static library
l4 = library('with-internal', 'both.c',
            link_with : internal_lib,
            install: true)
pkg.generate(l4)

test('test-both-whole-installed', executable('tester1', 'tester.c', link_with : l1))
test('test-both-whole-internal', executable('tester2', 'tester.c', link_with : l2))
test('test-both-with-installed', executable('tester3', 'tester.c', link_with : l3))
test('test-both-with-internal', executable('tester4', 'tester.c', link_with : l4))
