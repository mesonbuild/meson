project('cmake_object_lib_test', ['cpp'])

sub_pro = subproject('cmObjLib')
sub_sha = sub_pro.get_variable('lib_sha_dep')
sub_sta = sub_pro.get_variable('lib_sta_dep')

# Required for the static library
zlib_dep = dependency('zlib')

exe_sha = executable('shared', ['main.cpp'], dependencies: [sub_sha])
exe_sta = executable('static', ['main.cpp'], dependencies: [sub_sta, zlib_dep])

test('test1', exe_sha)
test('test1', exe_sta)
