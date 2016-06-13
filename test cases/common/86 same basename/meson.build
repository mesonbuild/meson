project('same basename', 'c')

# Use the same source file to check that each top level target
# has its own unique working directory. If they don't
# then the .o files will clobber each other.
shlib = shared_library('name', 'lib.c', c_args : '-DSHAR')

# On Windows a static lib is a foo.lib but a share library
# is both a foo.dll and a foo.lib. Put static in subdir to avoid
# name clashes.
subdir('sub')

exe1 = executable('name', 'exe1.c', link_with : stlib)
exe2 = executable('name2', 'exe2.c', link_with : shlib)

test('static', exe1)
test('shared', exe2)
