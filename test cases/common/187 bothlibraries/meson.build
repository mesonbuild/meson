project('both libraries linking test', 'c')

both_libs = both_libraries('mylib', 'libfile.c')
exe_shared = executable('prog-shared', 'main.c', link_with : both_libs.get_shared_lib())
exe_static = executable('prog-static', 'main.c',
                        c_args : ['-DSTATIC_COMPILATION'],
                        link_with : both_libs.get_static_lib())
exe_both = executable('prog-both', 'main.c', link_with : both_libs)

test('runtest-shared', exe_shared)
test('runtest-static', exe_static)
test('runtest-both', exe_both)
