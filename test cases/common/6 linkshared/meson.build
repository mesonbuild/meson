project('shared library linking test', 'c')
lib = shared_library('mylib',
 'libfile.c' # Split to different lines before and after the comma to test parser.
 , install : true)
exe = executable('prog', 'main.c', link_with : lib, install : true)

add_test('runtest', exe)
