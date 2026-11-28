project('cmake_object_depends', 'c')

cm = import('cmake')

sub_pro = cm.subproject('cmObjDep')

exe1 = executable('main1', ['main.c'], dependencies: [
  sub_pro.dependency('cmObjDepAbsolute'),
  sub_pro.dependency('cmObjDepRelative'),
  sub_pro.dependency('cmObjDepTransitive'),
  sub_pro.dependency('cmObjDepSub'),
])

test('test1', exe1)
