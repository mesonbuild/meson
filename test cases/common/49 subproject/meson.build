project('subproj user', 'c')

sub = subproject('sublib')

if is_subproject()
  error('Claimed to be a subproject even though we are the master project.')
endif

inc = sub.get_variable('i')
lib = sub.get_variable('l')

e = executable('user', 'user.c', include_directories : inc, link_with : lib, install : true)
test('subdirtest', e)
