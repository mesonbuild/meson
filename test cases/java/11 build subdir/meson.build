project('build subdir java', 'java')

copyfile = find_program('copyfile.py')

generated = custom_target(
  command: [copyfile, '@INPUT@', '@OUTPUT@'],
  input: 'com-mesonbuild-HelloWorldMainLauncherClass.java',
  output: 'HelloWorldMainLauncherClass.java',
  build_subdir: 'com/mesonbuild',
)

jar('hello', generated,
  main_class: 'com.mesonbuild.HelloWorldMainLauncherClass')
