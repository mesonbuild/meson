project('data install test', 'c')
install_data(sources : 'datafile.dat', install_dir : 'share/progname')
install_data(sources : 'etcfile.dat', install_dir : get_option('sysconfdir'))

subdir('vanishing')

install_data(sources : 'vanishing/vanishing2.dat', install_dir : 'share/progname')
