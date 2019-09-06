project('lib', ['c'])

a = library('test-a', 'liba.c', install: true)

install_headers(files('liba.h'))

import('pkgconfig').generate(
    a,
    version: '0.0',
    description: 'test library',
    filebase: 'test-a',
    name: 'test library',
    subdirs: ['.']
)
