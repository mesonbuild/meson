project('dll_no_module_def', 'c')

if meson.get_compiler('c').get_id() != 'msvc'
  error('Need to use the Visual Studio compiler')
endif

subdir('subdir')
exe = executable('prog', 'prog.c', link_with : shlib)
test('runtest', exe)
