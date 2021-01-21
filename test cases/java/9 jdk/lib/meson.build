sources = files(
  'native.c',
  'com_mesonbuild_JdkTest.c',
)

jdkjava = shared_module(
  'jdkjava',
  sources,
  dependencies : [jdk],
)

jdkjava_dep = declare_dependency(
  link_with : jdkjava,
)
