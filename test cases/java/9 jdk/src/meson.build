jdkjar = jar(
  'jdkjar',
  'com' / 'mesonbuild' / 'JdkTest.java',
  main_class : 'com.mesonbuild.JdkTest',
)

test(
  'jdktest',
  java,
  args: [
    '-Djava.library.path=@0@'.format(fs.parent(jdkjava.full_path())),
    '-jar',
    jdkjar,
  ],
  protocol : 'exitcode',
  depends : [jdkjava],
)
