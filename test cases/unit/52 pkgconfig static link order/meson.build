project('link order test', 'c')

dep = library('dependency', [])
lib = static_library('something', [], link_with: dep)

import('pkgconfig').generate(
  name: 'libsomething',
  description: 'test library',
  libraries: lib,
  version: '1'
)
