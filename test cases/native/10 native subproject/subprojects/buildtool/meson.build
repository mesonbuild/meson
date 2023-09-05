project('buildtool', 'c', meson_version : '>= 1.3.0')

e = executable('buildtool', 'buildtool.c')

meson.override_find_program('buildtool', e)

subproject('hostp', native : false)
