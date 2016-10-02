myenums = gnome.mkenums('abc',
  sources : 'meson-sample.h',
  h_template : 'enums.h.in',
  c_template : 'enums.c.in',
  install_header : true,
  install_dir : get_option('includedir'))

enums_c = myenums[0]
enums_h = myenums[1]

enumexe = executable('enumprog', 'main.c', enums_c, enums_h,
dependencies : gobj)
test('enum test', enumexe)
