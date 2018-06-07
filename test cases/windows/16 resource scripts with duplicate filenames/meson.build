project('foobar', 'c')

win = import('windows')

subdir('a')
subdir('b')
subdir('c')

main = win.compile_resources('rsrc.rc')

# these make the resource compilation a dependency of something which is built
# by default
static_library('libmain', main)
static_library('liba', a)
static_library('libb', b)
static_library('libc', c)
