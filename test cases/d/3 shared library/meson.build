project('D Shared Library', 'd')

if meson.get_compiler('d').get_id() != 'gcc'

    ldyn = shared_library('stuff', 'libstuff.d', install : true)
    ed = executable('app_d', 'app.d', link_with : ldyn, install : true)
    test('linktest_dyn', ed)

else
    message('GDC can not build shared libraries. Test skipped.')
    install_data('no-installed-files', install_dir : '')
endif
