project('custom target', 'c')

python = find_program('python3')

# Note that this will not add a dependency to the compiler executable.
# Code will not be rebuilt if it changes.
comp = '@0@/@1@'.format(meson.current_source_dir(), 'my_compiler.py')

mytarget = custom_target('bindat',
output : 'data.dat',
input : 'data_source.txt',
command : [python, comp, '@INPUT@', '@OUTPUT@'],
install : true,
install_dir : 'subdir'
)

subdir('depfile')
