project('multiple dir configure file', 'c')

subdir('subdir')

configure_file(input : 'subdir/someinput.in',
  output : 'outputhere',
  configuration : configuration_data())
