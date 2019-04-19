project('cmake_object_lib_test', ['c', 'cpp'])

if build_machine.system() == 'windows'
  error('MESON_SKIP_TEST: Windows is not supported because of symbol export problems')
endif

sub_pro = subproject('cmObjLib')
sub_sha = sub_pro.get_variable('lib_sha_dep')
sub_sta = sub_pro.get_variable('lib_sta_dep')

exe_sha = executable('shared', ['main.cpp'], dependencies: [sub_sha])
exe_sta = executable('static', ['main.cpp'], dependencies: [sub_sta])

test('test1', exe_sha)
test('test1', exe_sta)
