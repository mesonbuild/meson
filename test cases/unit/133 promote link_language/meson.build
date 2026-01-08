project('promote link_language', 'c', 'cpp')

cxx = meson.get_compiler('cpp')

lib = library('cxxlib-w-c-linkage', 'lib.cpp',
  cpp_args: cxx.get_supported_arguments(['-fno-exceptions', '-fno-rtti', '/EHc']),
  link_language : 'c',
)

con = library('consumer', 'consumer.c',
  link_with: lib
)
