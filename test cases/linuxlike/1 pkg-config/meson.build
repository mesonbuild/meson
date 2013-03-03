project('external dependency', 'c')

# Zlib is probably on all dev machines.

dep = find_dep('zlib', required : true)
exe = executable('zlibprog', 'prog.c', deps : dep)

add_test('zlibtest', exe)
