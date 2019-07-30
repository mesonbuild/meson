project('modules', 'fortran',
  default_options : ['default_library=static'])

commented = library('commented', 'comment_mod.f90')

e = executable('modprog', 'mymod.f90', 'prog.f90',
  link_with: commented)
test('moduletest', e)
