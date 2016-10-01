project('custom target', 'c')

python = find_program('python3')

# Note that this will not add a dependency to the compiler executable.
# Code will not be rebuilt if it changes.
comp = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler.py')

mytarget = custom_target('bindat',
  output : 'data.dat',
  input : 'data_source.txt',
  capture : true,
  command : [python, comp, '@INPUT@'],
  install : true,
  install_dir : 'subdir'
)
