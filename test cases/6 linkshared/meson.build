project('shared library linking test', 'c')
lib = shared_library('mylib', 'libfile.c', install : true)
exe = executable('prog', 'main.c', link_with : lib, install : true)

add_test('runtest', exe)
