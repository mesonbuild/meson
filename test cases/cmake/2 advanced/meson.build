project('cmakeSubTest_advanced', ['c', 'cpp'])

dep_test = dependency('ZLIB', method: 'cmake', required: false)
if not dep_test.found()
  error('MESON_SKIP_TEST: zlib is not installed')
endif

cm = import('cmake')

# Test the "normal" subproject call
sub_pro = cm.subproject('cmMod')
sub_dep = sub_pro.dependency('cmModLib')

# Build some files
exe1 = executable('main1', ['main.cpp'], dependencies: [sub_dep])
test('test1', exe1)

# Test if we can also extract executables
assert(sub_pro.target_type('testEXE') == 'executable', 'The type must be executable for obvious reasons')
test('test2', sub_pro.target('testEXE'))
