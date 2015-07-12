project('declare dependency', 'c')

subdir('entity')

exe = executable('dep_user', 'main.c',
  dependencies : entity_dep)
test('dep', exe)
