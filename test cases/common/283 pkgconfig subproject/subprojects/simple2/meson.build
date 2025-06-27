project('simple2', 'c', meson_version: '>=1.9.0')
pkgg = import('pkgconfig')

lib2 = library('simple2', 'simple2.c', vs_module_defs: 'exports.def')
lib_dep = declare_dependency(link_with: lib2, include_directories: include_directories('.'))

pkgg.generate(lib2)

meson.override_dependency('simple2', lib_dep)
