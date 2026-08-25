project('fmodbug', 'fortran', default_options: ['default_library=both'])

lib = library('mylib', 'modsrc.f90')
# CI also runs with other default_library settings
lib_linked = get_option('default_library') == 'both' ? lib.get_static_lib() : lib
exe = executable('myexe', 'main.f90', link_with: lib_linked)
