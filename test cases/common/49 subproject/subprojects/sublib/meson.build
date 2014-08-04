project('subproject', 'c')

if not is_subproject()
  error('Claimed to be master project even though we are a subproject.')
endif

i = include_directories('include')
l = shared_library('sublib', 'sublib.c', include_directories : i, install : true)
t = executable('simpletest', 'simpletest.c', include_directories : i, link_with : l)
test('plain', t)
