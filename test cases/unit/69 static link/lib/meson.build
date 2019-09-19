project('test static link libs', 'c')

# libfunc2 should contain both func1() and func2() symbols
libfunc1 = static_library('func1', 'func1.c',
  install : false)
libfunc2 = static_library('func2', 'func2.c',
  link_whole : libfunc1,
  install : true)

# Same as above, but with link_with instead of link_whole,
# libfunc4 should contain both func3() and func4() symbols
libfunc3 = static_library('func3', 'func3.c',
  install : false)
libfunc4 = static_library('func4', 'func4.c',
  link_with : libfunc3,
  install : true)
