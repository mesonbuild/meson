# Configure in subdir with absolute paths for input and relative for output
configure_file(input : '../dummy.dat',
  output : 'config2-1.h',
  command : [genprog, scriptfile,  ifile, 'config2-1.h'],
  install_dir : 'share/appdireh')
run_command(check_file, join_paths(meson.current_build_dir(), 'config2-1.h'))

# Configure in subdir with files() for input and relative for output
configure_file(input : '../dummy.dat',
  output : 'config2-2.h',
  command : [genprog, scriptfile, files('../dummy.dat'), 'config2-2.h'],
  install_dir : 'share/appdirok')
run_command(check_file, join_paths(meson.current_build_dir(), 'config2-2.h'))

# Configure in subdir with string templates for input and output
configure_file(input : '../dummy.dat',
  output : 'config2-3.h',
  command : [found_script,  '@INPUT@', '@OUTPUT@'])
run_command(check_file, join_paths(meson.current_build_dir(), 'config2-3.h'))
