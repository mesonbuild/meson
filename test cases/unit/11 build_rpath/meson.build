project('build rpath', 'c')

subdir('sub')
executable('prog', 'prog.c',
  link_with : l,
  build_rpath : '/foo/bar',
  install_rpath : '/baz',
  install : true,
  )
