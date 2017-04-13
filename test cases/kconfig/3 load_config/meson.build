project('kconfig load config', ['c'], meson_version : '>=0.40.0')

k = import('kconfig')


k.load('config')

if not k.is_set('CONFIG_VAL1')
  error('Expected CONFIG_VAL1 to be set, but it wasn\'t')
endif

if k.is_set('CONFIG_VAL2')
  error('Expected CONFIG_VAL2 not be set, but it was')
endif
