project('same basename', 'c',
  # Disable debugging otherwise the .pdb filenames for the DLL and EXE collide
  # when building with MSVC
  default_options : ['buildtype=release'])

# Disable incremental linking lest the .ilk files for the DLL and EXE collide
if meson.get_compiler('c').get_id() == 'msvc'
  add_global_link_arguments('/INCREMENTAL:NO', language : 'c')
endif

# Use the same source file to check that each top level target
# has its own unique working directory. If they don't
# then the .o files will clobber each other.
shlib = shared_library('name', 'lib.c', c_args : '-DSHAR')
# Also create a static library of the same name to verify that there's no
# filename collisions on Windows. This should output libname.a
stlib = static_library('name', 'lib.c', c_args : '-DSTAT')

# Create an executable with the same name as the libraries above
exe1 = executable('name', 'exe1.c', link_with : stlib)
exe2 = executable('name2', 'exe2.c', link_with : shlib)

test('static', exe1)
test('shared', exe2)
