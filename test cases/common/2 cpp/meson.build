project('c++ test', 'cpp')

if meson.get_compiler('cpp').get_id() == 'intel'
  # Error out if the -std=xxx option is incorrect
  add_project_arguments('-diag-error', '10159', language : 'cpp')
endif

exe = executable('trivialprog', 'trivial.cc', extra_files : 'something.txt')
test('runtest', exe)
