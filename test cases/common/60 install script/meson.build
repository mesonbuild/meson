project('custom install script', 'c')

if meson.get_compiler('c').get_id() == 'msvc'
  install_data('no-installed-files', install_dir : '')
else
  meson.add_install_script('myinstall.sh')
  executable('prog', 'prog.c', install : true)
endif
