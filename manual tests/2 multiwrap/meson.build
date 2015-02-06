project('multiwrap', 'c')

# Using multiple downloaded projects for great justice.

add_global_arguments('-std=c99', language : 'c')

luap = subproject('lua')
pngp = subproject('libpng')

executable('prog', 'prog.c',
include_directories : [pngp.get_variable('incdir'), luap.get_variable('incdir')],
link_with :[pngp.get_variable('libpng'), luap.get_variable('lualib')],
link_args : '-lm')
