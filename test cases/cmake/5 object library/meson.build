project('cmake_object_lib_test', ['c', 'cpp'])

dep_test = dependency('ZLIB', method: 'cmake', required: false)
if not dep_test.found()
  error('MESON_SKIP_TEST: zlib is not installed')
endif

py3 = import('python').find_installation('python3')
get_envvar = '''import os, sys; print(os.environ.get('@0@', 0), end='')'''
# Remove this env var from azure-pipelines.yml when fixed
if run_command(py3, '-c', get_envvar.format('CI_JOB_VS2017')).stdout() == '1'
  error('MESON_SKIP_TEST: broken for vs2017 jobs')
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
