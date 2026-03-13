generated_pyx = custom_target(
  'generated_pyx',
  input : 'gen.py',
  output : 'generated.pyx',
  command : [py, '@INPUT@', '@OUTPUT@'],
)

includestuff_ext = py.extension_module(
  'generated_pyx',
  generated_pyx
)

subdir('_pairwise_distances_reduction')
