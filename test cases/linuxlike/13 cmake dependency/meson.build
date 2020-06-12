# this test can ONLY be run successfully from run_project_test.py
# due to use of setup_env.json
project('external CMake dependency', ['c', 'cpp'])

if not find_program('cmake', required: false).found()
  error('MESON_SKIP_TEST cmake binary not available.')
endif

# CMake version
cm_vers = run_command(find_program('./cmVers.sh')).stdout().strip()

# Zlib is probably on all dev machines.

dep = dependency('ZLIB', version : '>=1.2', method : 'cmake')
exe = executable('zlibprog', 'prog-checkver.c',
  dependencies : dep,
  c_args : '-DFOUND_ZLIB="' + dep.version() + '"')

assert(dep.version().version_compare('>=1.2'), 'CMake version numbers exposed incorrectly.')

# Check that CMake targets are extracted
dept = dependency('ZLIB', version : '>=1.2', method : 'cmake', modules : 'ZLIB::ZLIB')
exet = executable('zlibprog_target', 'prog-checkver.c',
  dependencies : dep,
  c_args : '-DFOUND_ZLIB="' + dep.version() + '"')

# Check that the version exposed by zlib internally is the same as the one we
# retrieve from the pkg-config file. This assumes that the packager didn't mess
# up, but we can be reasonably sure of that.
test('zlibtest', exe)

# Test that dependencies of dependencies work.
dep2 = declare_dependency(dependencies : dep)
exe2 = executable('zlibprog2', 'prog.c', dependencies : dep2)
test('zlibtest2', exe2)

# Try to find a nonexistent library to ensure requires:false works.

depf1 = dependency('nvakuhrabnsdfasdf', required : false, method : 'cmake')
depf2 = dependency('ZLIB', required : false, method : 'cmake', modules : 'dfggh::hgfgag')

assert(depf2.found() == false, 'Invalid CMake targets should fail')

# Try to find cmMesonTestDep in a custom prefix
# setup_env.json is used by run_project_tests.py:_run_test to point to ./cmake_pref_env/
depPrefEnv = dependency('cmMesonTestDep', required : true, method : 'cmake')
depPrefEnv1 = dependency('cmMesonTestF1', required : true, method : 'cmake')
depPrefEnv2 = dependency('cmMesonTestF2', required : true, method : 'cmake')

# Try to find a dependency with a custom CMake module

depm1 = dependency('SomethingLikeZLIB', required : true, components : 'required_comp',   method : 'cmake', cmake_module_path : 'cmake')
depm2 = dependency('SomethingLikeZLIB', required : true, components : 'required_comp',   method : 'cmake', cmake_module_path : ['cmake'])
depm3 = dependency('SomethingLikeZLIB', required : true, components : ['required_comp'], cmake_module_path : 'cmake')

# Test some edge cases with spaces, etc. (but only for CMake >= 3.15)

if cm_vers.version_compare('>=3.15')
  testDep1 = dependency('ImportedTarget', required : true, method : 'cmake', cmake_module_path : 'cmake', modules: 'mesonTestLibDefs')
  testDep2 = dependency('ImportedTarget', required : true, method : 'cmake', cmake_module_path : 'cmake', modules : ['MesonTest::TestLibDefs'])
  testFlagSet1 = executable('testFlagSet1', ['testFlagSet.c'], dependencies: [testDep1])
  testFlagSet2 = executable('testFlagSet2', ['testFlagSet.c'], dependencies: [testDep2])
  test('testFlagSetTest1', testFlagSet1)
  test('testFlagSetTest2', testFlagSet2)
endif

# Try to compile a test that takes a dep and an include_directories

cc = meson.get_compiler('c')
zlibdep = cc.find_library('z')
code = '''#include<myinc.h>

int main(void) {
    void * something = deflate;
    if(something != 0)
        return 0;
    return 1;
}
'''

inc = include_directories('incdir')

r = cc.run(code, include_directories : inc, dependencies : zlibdep)
assert(r.returncode() == 0, 'Running manual zlib test failed.')
