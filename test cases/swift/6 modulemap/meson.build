project('mixed', 'c', 'swift')
add_project_arguments(['-I' + meson.source_root()], language : 'swift')
add_project_link_arguments(['-L' + meson.current_build_dir()], language : 'swift')

lib = static_library('mylib', 'mylib.c')
exe = executable('prog', 'main.swift',
  link_with : lib)
test('c module', exe)
