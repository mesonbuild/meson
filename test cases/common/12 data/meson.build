project('data install test', 'c')
install_data(sources : 'datafile.dat', install_dir : 'share/progname')
# Some file in /etc that is only read-write by root; add a sticky bit for testing
install_data(sources : 'etcfile.dat', install_dir : '/etc', install_mode : 'rw------T')
# Some script that needs to be executable by the group
install_data('runscript.sh',
  install_dir : get_option('bindir'),
  install_mode : ['rwxr-sr-x', 'root', 0])
install_data(files('fileobject_datafile.dat'),
  install_dir : 'share/progname',
  install_mode : [false, false, 0])

subdir('vanishing')

install_data(sources : 'vanishing/vanishing2.dat', install_dir : 'share/progname')
