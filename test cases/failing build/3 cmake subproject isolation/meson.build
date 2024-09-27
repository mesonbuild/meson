project('subproject isolation', ['c', 'cpp'])

incdir = meson.source_root() / 'incDir'

cm = import('cmake')

# This should generate a warning and the include dir should be skipped.
sub_pro = cm.subproject('cmMod', cmake_options : [ '-DMESON_INC_DIR=' + incdir ])
sub_dep = sub_pro.dependency('cmModLib++')

# Since the include dir is skipped, the compilation of this project should fail.
exe1 = executable('main', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)
