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
  variables : ['foo=bar', 'datadir=${prefix}/data'],
  extra_cflags : ['-DLIBFOO'],
)

pkgg.generate(
  name : 'libhello',
  description : 'A minimalistic pkgconfig file.',
  version : libver,
)

pkgg.generate(
  name : 'libhello_nolib',
  description : 'A minimalistic pkgconfig file.',
  version : libver,
  dataonly: true
)
