project('a', 'c')
configure_file(output: 'fullpath.c', input: 'main.c', copy: true)

path = meson.project_build_root() / 'fullpath.c'
if build_machine.system() == 'windows'
  if '\\' in meson.project_build_root()
    path = path.replace('\\', '/')
  else
    path = path.replace('/', '\\')
  endif
endif
exe = executable('fullpath', path)
test('fullpath', exe)
