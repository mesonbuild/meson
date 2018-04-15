project('c++ test', 'cpp')

compiler_id = meson.get_compiler('cpp').get_id()

if compiler_id == 'intel'
  # Error out if the -std=xxx option is incorrect
  add_project_arguments('-diag-error', '10159', language : 'cpp')
endif

exe = executable('trivialprog', 'trivial.cc', extra_files : 'something.txt')

test('runtest', exe)

if (compiler_id == 'gcc') or (compiler_id == 'clang')
  exe2 = executable('trivialprog2', 'trivial2.C')
  test('runtest2', exe2)
endif
