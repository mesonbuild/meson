# Can't build two libraries with the name 'testversion' in the same project, so
# use this hack to effectively get the same library name
oldversion = shared_library('estversion', '../lib.c',
  name_prefix : 'libt',
  soversion : 3)
oldlib_builddir = meson.current_build_dir()
