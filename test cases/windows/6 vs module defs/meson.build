project('dll_module_defs', 'c')

if meson.get_compiler('c').get_id() == 'msvc'
  subdir('subdir')
  exe = executable('prog', 'prog.c', link_with : shlib)
  test('runtest', exe)
endif
