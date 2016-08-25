enums_h = gnome.mkenums('enums.h',
sources : 'meson-sample.h',
template : 'enums.h.in',
install : true,
install_dir : get_option('includedir'))

enums_c = gnome.mkenums('enums.c',
sources : 'meson-sample.h',
template : 'enums.c.in',
depends : enums_h)

enumexe = executable('enumprog', 'main.c', enums_c, enums_h,
dependencies : gobj)
test('enum test', enumexe)
