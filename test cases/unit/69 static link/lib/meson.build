project('test static link libs', 'c')

# libfunc2 should contain both func1() and func2() symbols
libfunc1 = static_library('func1', 'func1.c',
  install : false)
libfunc2 = static_library('func2', 'func2.c',
  link_whole : libfunc1,
  install : true)
