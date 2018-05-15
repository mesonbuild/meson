# It used to be necessary to pass:
#
#   include_directories: include_directories('.')
#
# to any use of jar() to compile source code with inter-file class
# dependencies. This is now the default behaviour.

project('noincludedirsjava', 'java')

javaprog = jar('myprog',
 'com/mesonbuild/Simple.java',
 'com/mesonbuild/TextPrinter.java',
  main_class : 'com.mesonbuild.Simple')
test('subdirtest', javaprog)
