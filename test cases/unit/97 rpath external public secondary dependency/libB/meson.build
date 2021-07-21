project('libB', ['c'])

libA_dep = dependency('libA')

libB = library(
  'B',
  'libb.c',
  install: true,
  dependencies: libA_dep)

install_headers(files('libb.h'))

import('pkgconfig').generate(
  libB,
  version: '0.0',
  description: 'test library B',
  filebase: 'libB',
  name: 'test library B',
  libraries: libA_dep, # libB exposes public symbols of libA
  subdirs: ['.']
)
