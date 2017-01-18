project('custom target', 'c')

python3 = find_program('python3', required : false)
if not python3.found()
  python3 = find_program('python')
endif

# Note that this will not add a dependency to the compiler executable.
# Code will not be rebuilt if it changes.
comp = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler.py')

mytarget = custom_target('bindat',
  output : 'data.dat',
  input : 'data_source.txt',
  capture : true,
  command : [python3, comp, '@INPUT@'],
  install : true,
  install_dir : 'subdir'
)
