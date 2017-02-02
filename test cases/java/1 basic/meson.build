project('simplejava', 'java')

javaprog = jar('myprog', 'com/mesonbuild/Simple.java',
  main_class : 'com.mesonbuild.Simple',
  install : true,
  install_dir : get_option('bindir'))
test('mytest', javaprog)
