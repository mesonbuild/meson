project('unresolved symbols', 'c', 'cpp')

executable('unresolved-program', 'unresolved-symbol.c',
  c_args : '-DEXECUTABLE',
  allow_undefined : true)

shared_library('unresolved', 'unresolved-symbol.c',
  allow_undefined : true)

cpp_file = configure_file(
  input : 'unresolved-symbol.c',
  output : 'unresolved-symbol.cpp',
  configuration : configuration_data())

executable('unresolved-cpp-program', cpp_file,
  cpp_args : '-DEXECUTABLE',
  allow_undefined : true)

shared_library('unresolved-cpp', cpp_file,
  allow_undefined : true)
