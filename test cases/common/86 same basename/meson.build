project('same basename', 'c')

# Use the same source file to check that each top level target
# has its own unique working directory. If they don't
# then the .o files will clobber each other.
stlib = static_library('name', 'lib.c', c_args : '-DSTAT')
shlib = shared_library('name', 'lib.c', c_args : '-DSHAR')

exe1 = executable('name', 'exe1.c', link_with : stlib)
exe2 = executable('name2', 'exe2.c', link_with : shlib)

test('static', exe1)
test('shared', exe2)
