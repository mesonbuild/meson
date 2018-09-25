project('pch test', 'c', 'cpp')

subdir('c')
subdir('cpp')

if meson.backend() == 'xcode'
  warning('Xcode backend only supports one precompiled header per target. Skipping "mixed" which has various precompiled headers.')
else
  subdir('mixed')
endif
