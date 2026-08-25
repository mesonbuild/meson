project('linkingjava', 'java')

subdir('sub')

javaprog = jar('myprog', 'com/mesonbuild/Linking.java',
  main_class : 'com.mesonbuild.Linking',
  link_with : simplelib,
  install : true,
  install_dir : get_option('bindir'))
test('mytest', javaprog)
