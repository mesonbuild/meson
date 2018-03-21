project('shared library linking test', 'c', 'cpp')

lib = shared_module('mylib',
 'libfile.c' # Split to different lines before and after the comma to test parser.
 , install : false) # Don't install libraries in common tests; the path is platform-specific
exe = executable('prog', 'main.c', link_with : lib, install : true)