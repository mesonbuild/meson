project('cmake_object_lib_test', 'cpp')

cpp = meson.get_compiler('cpp')
if build_machine.system() == 'windows' and cpp.get_id() != 'gcc'
  error('MESON_SKIP_TEST: Windows link.exe is not supported because of symbol export problems')
endif

cm = import('cmake')

sub_pro = cm.subproject('cmObjLib')
sub_sha = sub_pro.dependency('lib_sha')
sub_sta = sub_pro.dependency('lib_sta')

exe_sha = executable('shared', ['main.cpp'], dependencies: [sub_sha])
exe_sta = executable('static', ['main.cpp'], dependencies: [sub_sta])

test('test1', exe_sha)
test('test1', exe_sta)
