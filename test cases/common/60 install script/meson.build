project('custom install script', 'c')

if meson.get_compiler('c').get_id() == 'msvc'
  meson.add_install_script('myinstall.bat')
else
  meson.add_install_script('myinstall.sh')
endif
executable('prog', 'prog.c', install : true)
