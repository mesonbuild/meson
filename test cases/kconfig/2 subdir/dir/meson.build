
k = import('kconfig')

k.load(join_paths(meson.source_root(), '.config'))

if not k.is_set('CONFIG_IS_SET')
  error('Expected CONFIG_IS_SET to be set, but it wasn\'t')
endif

if k.is_set('CONFIG_NOT_IS_SET')
  error('Expected CONFIG_VAL2 not be set, but it was')
endif

