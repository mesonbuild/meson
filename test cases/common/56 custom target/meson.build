project('custom target', 'c')

python = find_program('python3')

comp = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler.py')
infile = '@0@/@1@'.format(meson.current_source_dir(), 'data_source.txt')
outfile = '@0@/@1@'.format(meson.current_build_dir(), 'data.dat')

mytarget = custom_target('bindat',
output : 'data.dat',
command : [python, comp, infile, outfile],
install : true,
install_dir : 'subdir'
)
