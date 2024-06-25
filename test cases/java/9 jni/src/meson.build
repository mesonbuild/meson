sources = [files('com/mesonbuild/JniTest.java')]

subdir('com/mesonbuild')

jnijar = jar(
  'jnijar',
  sources,
  main_class : 'com.mesonbuild.JniTest',
  java_resources : structured_sources(jnijava)
)
