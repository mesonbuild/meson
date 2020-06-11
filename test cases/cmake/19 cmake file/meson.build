project(
  'cmake config file',
)

cmake = import('cmake')

cmake_conf = configuration_data()
cmake_conf.set_quoted('foo', 'bar')
cmake.configure_package_config_file(
  name : 'foolib',
  input : 'foolib.cmake.in',
  install_dir : get_option('libdir') / 'cmake',
  configuration : cmake_conf,
)
