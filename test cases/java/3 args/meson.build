project('simplejava', 'java')

add_project_arguments('-target', '1.7', language : 'java')

javaprog = jar('myprog', 'com/mesonbuild/Simple.java',
  main_class : 'com.mesonbuild.Simple',
  java_args : ['-source', '1.7'])
test('mytest', javaprog)

