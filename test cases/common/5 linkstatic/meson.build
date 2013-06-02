project('static library linking test', 'c')
lib = static_library('mylib', 'libfile.c')
exe = executable('prog', 'main.c', link_with : lib)

test('runtest', exe)
