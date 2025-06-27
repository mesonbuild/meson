project('simple', 'c', meson_version: '>=1.9.0')
pkgg = import('pkgconfig')

simple2_dep = dependency('simple2')

simple_lib = library('simple',
    'simple.c',
    dependencies: [simple2_dep]
)

pkgg.generate(simple_lib,
requires: simple2_dep,
)
