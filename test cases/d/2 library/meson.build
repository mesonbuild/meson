project('D Library', 'd')

if meson.get_compiler('d').get_id() != 'gcc'
    ldyn = shared_library('stuff', 'libstuff.d', install : true)
    ed = executable('app_d', 'app.d', link_with : ldyn, install : true)
    test('linktest_dyn', ed)

else
    message('GDC can not build shared libraries. Build skipped.')
endif

lstatic = static_library('stuff', 'libstuff.d', install : true)
es = executable('app_s', 'app.d', link_with : lstatic, install : true)
test('linktest_static', es)
