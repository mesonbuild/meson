project('custom target', 'c')

python = find_program('python3')

comp = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler.py')
comp2 = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler2.py')
infile = '@0@/@1@'.format(meson.current_source_dir(), 'data_source.txt')

mytarget = custom_target('bindat',
  output : 'data.dat',
  command : [python, comp, infile, '@OUTPUT@'],
)

mytarget2 = custom_target('bindat2',
  output : 'data2.dat',
  command : [python, comp2, mytarget, '@OUTPUT@'],
  install : true,
  install_dir : 'subdir'
)

subdir('usetarget')
