project('mainproj', 'c',
  default_options : ['wrap_mode=nodownload'],
)

subproject('zlib')
subproject('foo')

executable('grabprog', files('src/subprojects/prog.c'))
executable('grabprog2', files('src/subprojects/foo/prog2.c'))
subdir('src')
