project('subproj user', 'c')

sub = subproject('sublib')

inc = sub.get_variable('i')
lib = sub.get_variable('l')

e = executable('user.c', include_dirs : inc, link_with : lib)
test('subdirtest', e)
