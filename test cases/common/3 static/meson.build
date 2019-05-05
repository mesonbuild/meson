project('static library test', 'c')

lib = static_library('mylib', get_option('source'),
  link_args : '-THISMUSTNOBEUSED') # Static linker needs to ignore all link args.
