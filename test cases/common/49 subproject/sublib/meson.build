project('subproject', 'c')

i = include_directories('include')
l = shared_library('sublib', 'sublib.c', include_dirs : i, install : true)
t = executable('simpletest', 'simpletest.c', include_dirs : i, link_with : l)
test('plain', t)
