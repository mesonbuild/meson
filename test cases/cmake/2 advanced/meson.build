project('cmakeSubTest_advanced', ['c', 'cpp'])

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

# Test the "normal" subproject call
sub_pro = cm.subproject('cmMod')
sub_dep = sub_pro.dependency('cmModLib')
sub_sta = sub_pro.dependency('cmModLibStatic')

# Build some files
exe1 = executable('main1', ['main.cpp'], dependencies: [sub_dep])
exe2 = executable('main2', ['main.cpp'], dependencies: [sub_sta])
test('test1', exe1)
test('test2', exe2)

# Test if we can also extract executables
assert(sub_pro.target_type('testEXE') == 'executable', 'The type must be executable for obvious reasons')
test('test3', sub_pro.target('testEXE'))
