project('static library test', 'c')
lib = static_library('mylib', 'libfile.c',
  link_args : '-THISMUSTNOBEUSED') # Static linker needs to ignore all link args.
