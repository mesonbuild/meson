project('msvc dll versioning', 'c')

cc = meson.get_compiler('c')

# Test that MSVC creates foo-0.dll and bar.dll
if cc.get_id() == 'msvc'
  shared_library('some', 'lib.c',
    version : '1.2.3',
    soversion : '0',
    install : true)

  shared_library('noversion', 'lib.c',
    install : true)
else
  install_data('no-installed-files', install_dir : '')
endif
