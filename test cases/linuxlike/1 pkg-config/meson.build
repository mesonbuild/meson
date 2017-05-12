project('external dependency', 'c')

# Zlib is probably on all dev machines.

dep = dependency('zlib', version : '>=1.2')
exe = executable('zlibprog', 'prog-checkver.c',
  dependencies : dep,
  c_args : '-DFOUND_ZLIB="' + dep.version() + '"')

assert(dep.version().version_compare('>=1.2'), 'Pkg-config version numbers exposed incorrectly.')

# Check that the version exposed by zlib internally is the same as the one we
# retrieve from the pkg-config file. This assumes that the packager didn't mess
# up, but we can be reasonably sure of that.
test('zlibtest', exe)

zprefix = dep.get_pkgconfig_variable('prefix') # Always set but we can't be sure what the value is.
# pkg-config returns empty string for not defined variables
assert(dep.get_pkgconfig_variable('nonexisting') == '', 'Value of unknown variable is not empty.')

# Test that dependencies of dependencies work.
dep2 = declare_dependency(dependencies : dep)
exe2 = executable('zlibprog2', 'prog.c', dependencies : dep2)
test('zlibtest2', exe2)

# Try to find a nonexistant library to ensure requires:false works.

dep = dependency('nvakuhrabnsdfasdf', required : false)

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
