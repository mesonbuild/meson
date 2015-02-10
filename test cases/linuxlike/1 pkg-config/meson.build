project('external dependency', 'c')

# Zlib is probably on all dev machines.

dep = dependency('zlib', version : '>=1.2.8')
exe = executable('zlibprog', 'prog.c', dependencies : dep)

test('zlibtest', exe)

# Try to find a nonexistant library to ensure requires:false works.

dep = dependency('nvakuhrabnsdfasdf', required : false)
