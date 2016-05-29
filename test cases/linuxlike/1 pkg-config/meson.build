project('external dependency', 'c')

# Zlib is probably on all dev machines.

dep = dependency('zlib', version : '>=1.2.8')
exe = executable('zlibprog', 'prog.c', dependencies : dep)

assert(dep.version().version_compare('>=1.2.8'), 'Pkg-config version numbers exposed incorrectly.')

test('zlibtest', exe)

# Test that dependencies of dependencies work.
dep2 = declare_dependency(dependencies : dep)
exe2 = executable('zlibprog2', 'prog.c', dependencies : dep2)
test('zlibtest2', exe2)

# Try to find a nonexistant library to ensure requires:false works.

dep = dependency('nvakuhrabnsdfasdf', required : false)
