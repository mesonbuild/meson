project('lib', ['c'])

libA_dep = dependency('test-a')

b = library('test-b', 'libb.c', install: true, dependencies : libA_dep)

install_headers(files('libb.h'))

import('pkgconfig').generate(
    b,
    version: '0.0',
    description: 'test library',
    filebase: 'test-b',
    name: 'test library',
    subdirs: ['.']
)
