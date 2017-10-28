project('D Shared Library', 'd')

dc = meson.get_compiler('d')
if dc.get_id() == 'gcc'
  if dc.version().version_compare('< 8')
    error('MESON_SKIP_TEST: GDC < 8.0 can not build shared libraries')
  endif
endif

ldyn = shared_library('stuff', 'libstuff.d', install : true)
ed = executable('app_d', 'app.d', link_with : ldyn, install : true)
test('linktest_dyn', ed)
