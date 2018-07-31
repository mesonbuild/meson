project('generated_dll_module_defs', 'c')

if meson.backend().startswith('vs')
  # FIXME: Broken on the VS backends
  error('MESON_SKIP_TEST see https://github.com/mesonbuild/meson/issues/1799')
endif

subdir('subdir')
exe = executable('prog', 'prog.c', link_with : shlib)
test('runtest', exe)
