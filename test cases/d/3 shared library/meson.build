project('D Shared Library', 'd')

if meson.get_compiler('d').get_id() == 'gcc'
  error('MESON_SKIP_TEST: GDC can not build shared libraries')
endif

ldyn = shared_library('stuff', 'libstuff.d', install : true)
ed = executable('app_d', 'app.d', link_with : ldyn, install : true)
test('linktest_dyn', ed)
