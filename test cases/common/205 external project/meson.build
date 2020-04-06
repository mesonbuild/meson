project('test external project', 'c')

pkg = import('pkgconfig')

somelib = library('somelib', 'func.c')
pkg.generate(somelib)

subdir('libfoo')

executable('test-find-library', 'app.c', dependencies : libfoo_dep)
