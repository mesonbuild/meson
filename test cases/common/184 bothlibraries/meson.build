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

# Same as above, but using build_target()
both_libs2 = build_target('mylib2', 'libfile.c', target_type: 'both_libraries')
exe_shared2 = executable('prog-shared2', 'main.c',
                         link_with : both_libs2.get_shared_lib())
exe_static2 = executable('prog-static2', 'main.c',
                         c_args : ['-DSTATIC_COMPILATION'],
                         link_with : both_libs2.get_static_lib())
exe_both2 = executable('prog-both2', 'main.c', link_with : both_libs2)

test('runtest-shared-2', exe_shared2)
test('runtest-static-2', exe_static2)
test('runtest-both-2', exe_both2)
