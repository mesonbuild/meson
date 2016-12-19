project('custom install script', 'c')

executable('prog', 'prog.c', install : true)
meson.add_install_script('myinstall.py', 'diiba/daaba', 'file.dat')
meson.add_install_script('myinstall.py', 'this/should', 'also-work.dat')

subdir('src')
