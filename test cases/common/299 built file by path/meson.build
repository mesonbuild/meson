project('a', 'c')
configure_file(output: 'fullpath.c', input: 'main.c', copy: true)
exe = executable('fullpath', meson.project_build_root() / 'fullpath.c')
test('fullpath', exe)
