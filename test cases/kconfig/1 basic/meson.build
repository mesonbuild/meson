project('kconfig basic test',
  # Comment inside a function call + array for language list
  ['c'],
  meson_version : '>=0.40.0')

k = import('kconfig')
k.load('.config')

if not k.is_set('CONFIG_VAL1')
  error('Expected CONFIG_VAL1 to be set, but it wasn\'t')
endif

if k.is_set('CONFIG_VAL2')
  error('Expected CONFIG_VAL2 not be set, but it was')
endif

if k.value('CONFIG_VAL_VAL').to_int() != 4
  error('Expected CONFIG_VAL_VAL to be 4')
endif
