# Alas, this test requires running the installed target
# to really validate the underlying feature
project('cmakeSubTest', ['c', 'cpp'])

cm = import('cmake')

sub_pro = cm.subproject('cmMod')
sub_dep = sub_pro.dependency('cmModLib++')

exe1 = executable('main',
  ['main.cpp'],
  dependencies: [sub_dep],
  install: true,
  install_rpath: '$ORIGIN/../lib'
)
test('test1', exe1)
