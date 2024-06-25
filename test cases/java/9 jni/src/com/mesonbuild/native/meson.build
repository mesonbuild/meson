native_sources = [
  files(
    'native.c',
    'com_mesonbuild_JniTest.c',
  ),
  native_headers
]

jnijava = shared_module(
  'jnijava',
  native_sources,
  dependencies : [jni_dep],
  include_directories : [native_header_includes]
)
