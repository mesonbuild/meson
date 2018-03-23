project('shared library linking test', 'c', 'cpp')

lib = shared_module('mylib', 'libfile.c')

exe = executable('prog', 'main.c', link_with : lib, install : true)