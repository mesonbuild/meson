jnijar = jar(
  'jnijar',
  'com' / 'mesonbuild' / 'JniTest.java',
  main_class : 'com.mesonbuild.JniTest',
)

test(
  'jnitest',
  java,
  args: [
    '-Djava.library.path=@0@'.format(fs.parent(jnijava.full_path())),
    '-jar',
    jnijar,
  ],
  protocol : 'exitcode',
  depends : [jnijava],
)
