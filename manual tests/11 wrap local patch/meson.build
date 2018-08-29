project('multiwrap', 'c',
  default_options : 'c_std=c99')

# Using multiple downloaded projects for great justice.

cc = meson.get_compiler('c')

pngdep = dependency('external_libpng', fallback : ['external_libpng', 'png_dep'])

executable('prog', 'prog.c',
  dependencies : [pngdep])
