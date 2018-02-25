project('mainproj', 'c')

foo = subproject('zlib')
foo_dep = foo.get_variable('foo_dep')

executable('mainproj', 'main.c', dependencies: foo_dep)
