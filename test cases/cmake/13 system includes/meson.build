project(
  'meson_cmake_system_include_bug', ['c', 'cpp'],
  default_options: [
    'warning_level=3',
    'werror=true',
  ],
)

if meson.get_compiler('cpp').get_argument_syntax() == 'msvc'
  error('MESON_SKIP_TEST: Skip with msvc due to missing -system support')
endif

cm = import('cmake')
sub_pro = cm.subproject('cmMod')
sub_dep = sub_pro.dependency('cmModLib')
sub_inc = sub_pro.include_directories('cmModLib')

exe1 = executable('main1', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)

exe2 = executable('main2', ['main2.cpp'], include_directories: sub_inc)
test('test2', exe1)
