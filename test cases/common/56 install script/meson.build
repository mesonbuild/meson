project('custom install script', 'c')

executable('prog', 'prog.c', install : true)
meson.add_install_script('myinstall.py', 'diiba/daaba', 'file.dat')
meson.add_install_script('myinstall.py', 'this/should', 'also-work.dat')

subdir('src')

meson.add_install_script('myinstall.py', 'dir', afile, '--mode=copy')

data = configuration_data()
data.set10('foo', true)
conf = configure_file(
  configuration : data,
  output : 'conf.txt'
)

meson.add_install_script('myinstall.py', 'dir', conf, '--mode=copy')

t = custom_target(
  'ct',
  command : [find_program('customtarget.py'), '@OUTDIR@'],
  output : ['1.txt', '2.txt'],
)

meson.add_install_script('myinstall.py', 'customtarget', t, '--mode=copy')
meson.add_install_script('myinstall.py', 'customtargetindex', t[0], '--mode=copy')
