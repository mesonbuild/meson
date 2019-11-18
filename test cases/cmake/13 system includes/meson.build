project(
  'meson_cmake_system_include_bug', ['c', 'cpp'],
  default_options: [
    'warning_level=3',
    'werror=true',
  ],
)

cm = import('cmake')
sub_pro = cm.subproject('cmMod')
sub_dep = sub_pro.dependency('cmModLib')

exe1 = executable('main1', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)
