project('custom target', 'c')

python = find_program('python3')

comp = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler.py')
comp2 = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler2.py')
infile = '@0@/@1@'.format(meson.current_source_dir(), 'data_source.txt')
outfile = '@0@/@1@'.format(meson.current_build_dir(), 'data.dat')
outfile2 = '@0@/@1@'.format(meson.current_build_dir(), 'data2.dat')

mytarget = custom_target('bindat',
output : 'data.dat',
command : [python, comp, infile, outfile],
)

mytarget2 = custom_target('bindat2',
output : 'data2.dat',
command : [python, comp2, mytarget, outfile2],
install : true,
install_dir : 'subdir'
)
