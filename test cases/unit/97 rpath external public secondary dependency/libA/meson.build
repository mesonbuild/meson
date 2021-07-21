project('libA', ['c'])

libA = library(
  'A',
  'liba.c',
  install: true)

install_headers(files('liba.h'))

import('pkgconfig').generate(
  libA,
  version: '0.0',
  description: 'test library A',
  filebase: 'libA',
  name: 'test library A',
  subdirs: ['.']
)
