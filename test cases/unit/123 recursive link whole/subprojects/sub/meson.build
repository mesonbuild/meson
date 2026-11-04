project('sub', 'c')

libsub = library('sub', 'libsub.c')
libsub_dep = declare_dependency(link_with: libsub)
meson.override_dependency('sub', libsub_dep)
