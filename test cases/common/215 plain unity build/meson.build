project('specify_lang', 'cpp', default_options: ['unity=on'])

if meson.is_unity()
  message('Unity on...')
endif

dirs = [ 'lib1', 'lib2', 'lib3' ]
foreach dir : dirs
  subdir(dir)
endforeach
