project('simplejava', 'java')

add_project_arguments('-target', '1.6', language : 'java')

javaprog = jar('myprog', 'com/mesonbuild/Simple.java',
  main_class : 'com.mesonbuild.Simple',
  java_args : ['-source', '1.6'])
test('mytest', javaprog)

