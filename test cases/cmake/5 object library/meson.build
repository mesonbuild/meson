project('cmake_object_lib_test', 'cpp')

dep_test = dependency('ZLIB', method: 'cmake', required: false)
if not dep_test.found()
  error('MESON_SKIP_TEST: zlib is not installed')
endif

cpp = meson.get_compiler('cpp')
if build_machine.system() == 'windows' and cpp.get_id() != 'gcc'
  error('MESON_SKIP_TEST: Windows link.exe is not supported because of symbol export problems')
endif

cm = import('cmake')

sub_pro = cm.subproject('cmObjLib')
sub_sha = sub_pro.dependency('lib_sha')
sub_sta = sub_pro.dependency('lib_sta')

# Required for the static library
zlib_dep = dependency('zlib')

exe_sha = executable('shared', ['main.cpp'], dependencies: [sub_sha])
exe_sta = executable('static', ['main.cpp'], dependencies: [sub_sta, zlib_dep])

test('test1', exe_sha)
test('test1', exe_sta)
