project('external CMake dependency', 'c')

if not find_program('cmake', required: false).found()
  error('MESON_SKIP_TEST cmake binary not available.')
endif

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

# Try to find a dependency with a custom CMake module

depm1 = dependency('SomethingLikeZLIB', required : true, method : 'cmake', cmake_module_path : 'cmake')
depm2 = dependency('SomethingLikeZLIB', required : true, method : 'cmake', cmake_module_path : ['cmake'])
depm3 = dependency('SomethingLikeZLIB', required : true, cmake_module_path : 'cmake')

# Try to compile a test that takes a dep and an include_directories

cc = meson.get_compiler('c')
zlibdep = cc.find_library('z')
code = '''#include<myinc.h>

int main(int argc, char **argv) {
    void * something = deflate;
    if(something != 0)
        return 0;
    return 1;
}
'''

inc = include_directories('incdir')

r = cc.run(code, include_directories : inc, dependencies : zlibdep)
assert(r.returncode() == 0, 'Running manual zlib test failed.')
