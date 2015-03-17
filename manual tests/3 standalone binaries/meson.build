project('myapp', 'c')

sdl = dependency('sdl2')

if host.name() == 'darwin'
  install_data('myapp.sh',
  install_dir : 'Contents/MacOS')

  install_data('myapp.icns',
  install_dir : 'Contents/Resources')

  install_data('Info.plist',
  install_dir : 'Contents')

  meson.set_install_script('osx_bundler.sh')
endif

if host.name() == 'linux'
  install_data('myapp.sh', install_dir : '.')
  meson.set_install_script('linux_bundler.sh')
endif


prog = executable('myapp', 'myapp.c',
dependencies : sdl,
install : true)
