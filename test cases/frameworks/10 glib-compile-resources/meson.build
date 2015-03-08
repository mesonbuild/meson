project('glib-compile-resources', 'c')

gio = dependency('gio-2.0')

resources = glib_compile_resources('meson-resources', 'meson.gresource.xml',
                                   src_dir : 'data', c_name : 'meson')

exe = executable('gresource', 'prog.c', resources,
                 dependencies : gio,
                 include_directories : include_directories('.'))
test('grestest', exe)
