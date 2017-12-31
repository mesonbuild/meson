project('pkgconfig-gen', 'c')

# First check we have pkg-config >= 0.29

pkgconfig = find_program('pkg-config', required: false)
if not pkgconfig.found()
  error('MESON_SKIP_TEST: pkg-config not found')
endif

v = run_command(pkgconfig, '--version').stdout().strip()
if v.version_compare('<0.29')
  error('MESON_SKIP_TEST: pkg-config version \'' + v + '\' too old')
endif

pkgg = import('pkgconfig')

lib = shared_library('simple', 'simple.c')
libver = '1.0'
h = install_headers('simple.h')

pkgg.generate(
  libraries : [lib, '-lz'],
  subdirs : '.',
  version : libver,
  name : 'libsimple',
  filebase : 'simple',
  description : 'A simple demo library.',
  requires : 'glib-2.0', # Not really, but only here to test that this works.
  requires_private : ['gio-2.0', 'gobject-2.0'],
  libraries_private : [lib, '-lz'],
)

test('pkgconfig-validation', pkgconfig,
  args: ['--validate', 'simple'],
  env: [ 'PKG_CONFIG_PATH=' + meson.current_build_dir() + '/meson-private' ])

# Test that name_prefix='' and name='libfoo' results in '-lfoo'
lib2 = shared_library('libfoo', 'simple.c',
  name_prefix : '',
  version : libver)

pkgg.generate(
  libraries : lib2,
  name : 'libfoo',
  version : libver,
  description : 'A foo library.',
  variables : ['foo=bar', 'datadir=${prefix}/data']
)

# libmain internally use libinternal and expose libexpose in its API
exposed_lib = shared_library('libexposed', 'simple.c')
internal_lib = shared_library('libinternal', 'simple.c')
main_lib = shared_library('libmain', link_with : [exposed_lib, internal_lib])

pkgg.generate(libraries : exposed_lib,
  version : libver,
  name : 'libexposed',
  description : 'An exposed library in dependency test.'
)

# Declare a few different Dependency objects
pc_dep = dependency('libfoo', required : false)
threads_dep = dependency('threads', required : false)
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
pkgg.generate(libraries : [main_lib, exposed_lib, threads_dep , custom_dep],
  libraries_private : [custom_dep, custom2_dep, pc_dep],
  version : libver,
  name : 'dependency-test',
  filebase : 'dependency-test',
  description : 'A dependency test.'
)
