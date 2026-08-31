# Issue #14140: depfile: '@OUTPUT@.d' in a subdirectory must not
# double the subdirectory in @DEPFILE@ or in ninja's depfile path.
custom_target('outputdepfile',
  output : 'out.dat',
  depfile : '@OUTPUT@.d',
  build_by_default : true,
  command : [find_program('gen.py'), '@DEPFILE@', '@OUTPUT@'],
)

# build_subdir is part of the target directory, not of @OUTPUT@'s filename.
custom_target('outputdepfile-build-subdir',
  output : 'out.dat',
  depfile : '@OUTPUT@.d',
  build_subdir : 'placed',
  build_by_default : true,
  command : [find_program('gen.py'), '@DEPFILE@', '@OUTPUT@'],
)
