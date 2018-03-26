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

args = build_args()
args.add_compiler_args('-DSTATIC_COMPILATION',
  target_type : 'static_library',
  language : 'c',
)

both_libs = both_libraries('mylib-diffargs', 'libfile.c', extra_args : args)
exe_shared = executable('prog-shared-diffargs', 'main.c',
                        link_with : both_libs.get_shared_lib())
exe_static = executable('prog-static-diffargs', 'main.c',
                        c_args : ['-DSTATIC_COMPILATION'],
                        link_with : both_libs.get_static_lib())

test('runtest-shared-diffargs', exe_shared, args : '43')
test('runtest-static-diffargs', exe_static, args : '42')
