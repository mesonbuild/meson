project('kconfig builddir test')

k = import('unstable-kconfig')

configure_file(input: 'config', output: 'out-config', copy: true)
conf = k.load(meson.build_root() / 'out-config')

if not conf.has_key('CONFIG_IS_SET')
  error('Expected CONFIG_IS_SET to be set, but it wasn\'t')
endif

if conf.has_key('CONFIG_NOT_IS_SET')
  error('Expected CONFIG_NOT_IS_SET not be set, but it was')
endif
