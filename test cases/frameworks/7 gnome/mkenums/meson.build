# Generate both header and source via template together.

myenums = gnome.mkenums('abc1',
  sources : 'meson-sample.h',
  h_template : 'enums.h.in',
  c_template : 'enums.c.in',
  install_header : true,
  install_dir : get_option('includedir'))

enums_c1 = myenums[0]
enums_h1 = myenums[1]

conf = configuration_data()
conf.set('ENUM_FILE', 'enums.h')
main = configure_file(
  input : 'main.c',
  output : 'main1.c',
  configuration : conf)

enumexe1 = executable('enumprog1', main, enums_c1, enums_h1,
dependencies : gobj)
test('enum test 1', enumexe1)

# Generate both header and source via template individually and overriding.

enums_h2 = gnome.mkenums('abc2',
  sources : 'meson-sample.h',
  h_template : 'enums2.h.in',
  ftail : '/* trailing header file info */',
  install_header : true,
  install_dir : get_option('includedir'))

enums_c2 = gnome.mkenums('abc2',
  sources : 'meson-sample.h',
  depends : [enums_h1, enums_h2],
  c_template : 'enums2.c.in',
  ftail : '/* trailing source file info */',
  install_header : true,
  install_dir : get_option('includedir'))

conf = configuration_data()
conf.set('ENUM_FILE', 'enums2.h')
main = configure_file(
  input : 'main.c',
  output : 'main2.c',
  configuration : conf)

enumexe2 = executable('enumprog2', main, enums_c2, enums_h2,
dependencies : gobj)
test('enum test 2', enumexe2)

# Generate both header and source by options only.
# These are specified in a way that should produce the same result as above
# (modulo any filename changes.)

enums_h3 = gnome.mkenums('enums3.h',
  sources : 'meson-sample.h',
  fhead : '''#ifndef MESON_ENUMS_H
#define MESON_ENUMS_H

#include <glib-object.h>

G_BEGIN_DECLS
''',
  fprod : '''
/* enumerations from "@basename@" */
''',
  vhead : '''GType @enum_name@_get_type(void) G_GNUC_CONST;
#define @ENUMPREFIX@_TYPE_@ENUMSHORT@ (@enum_name@_get_type())
''',
  ftail : '''
G_END_DECLS

#endif /* MESON_ENUMS_H */
''',
  install_header : true,
  install_dir : get_option('includedir'))

enums_c3 = gnome.mkenums('enums3.c',
  sources : 'meson-sample.h',
  depends : enums_h3,
  fhead : '''#include "enums3.h"
''',
  fprod : '''

/* enumerations from "@basename@" */
#include "@basename@"
''',
  vhead : '''
GType
@enum_name@_get_type(void) {
    static volatile gsize g_define_type_id__volatile = 0;

    if(g_once_init_enter(&g_define_type_id__volatile)) {
        static const G@Type@Value values [] = {
''',
  vprod : '''            { @VALUENAME@, "@VALUENAME@", "@valuenick@" },''',
  vtail : '''            { 0, NULL, NULL }
        };

        GType g_define_type_id =
            g_@type@_register_static(g_intern_static_string("@EnumName@"), values);
        g_once_init_leave(&g_define_type_id__volatile, g_define_type_id);
    }

    return g_define_type_id__volatile;
}
''')

conf = configuration_data()
conf.set('ENUM_FILE', 'enums3.h')
main = configure_file(
  input : 'main.c',
  output : 'main3.c',
  configuration : conf)

enumexe3 = executable('enumprog3', main, enums_c3, enums_h3,
dependencies : gobj)
test('enum test 3', enumexe3)
