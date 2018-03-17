project('pkgconfig-gen-dependencies', 'c')

pkgg = import('pkgconfig')

# libmain internally use libinternal and expose libexpose in its API
exposed_lib = shared_library('libexposed', 'exposed.c')
internal_lib = shared_library('libinternal', 'internal.c')
main_lib = static_library('libmain', link_with : [exposed_lib, internal_lib])

pkgg.generate(libraries : exposed_lib,
  version : '1.0',
  name : 'libexposed',
  description : 'An exposed library in dependency test.'
)

# Declare a few different Dependency objects
pc_dep = dependency('libfoo')
notfound_dep = dependency('notfound', required : false)
threads_dep = dependency('threads')
custom_dep = declare_dependency(link_args : ['-lcustom'], compile_args : ['-DCUSTOM'])
custom2_dep = declare_dependency(link_args : ['-lcustom2'], compile_args : ['-DCUSTOM2'])

# Generate a PC file:
# - Having libmain in libraries should pull implicitely libexposed and libinternal in Libs.private
# - Having libexposed in libraries should remove it from Libs.private
# - We generated a pc file for libexposed so it should be in Requires instead of Libs
# - Having threads_dep in libraries should add '-pthread' in both Libs and Cflags
# - Having custom_dep in libraries and libraries_private should only add it in Libs
# - Having custom2_dep in libraries_private should not add its Cflags
# - Having pc_dep in libraries_private should add it in Requires.private
# - notfound_dep is not required so it shouldn't appear in the pc file.
pkgg.generate(libraries : [main_lib, exposed_lib, threads_dep , custom_dep],
  libraries_private : [custom_dep, custom2_dep, pc_dep, notfound_dep],
  version : '1.0',
  name : 'dependency-test',
  filebase : 'dependency-test',
  description : 'A dependency test.'
)
