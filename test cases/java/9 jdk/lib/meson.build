sources = [
  files(
    'native.c',
    'com_mesonbuild_JdkTest.c',
  ),
  native_header
]

jdkjava = shared_module(
  'jdkjava',
  sources,
  dependencies : [jdk],
  include_directories : [native_header_includes]
)

jdkjava_dep = declare_dependency(
  link_with : jdkjava,
)
