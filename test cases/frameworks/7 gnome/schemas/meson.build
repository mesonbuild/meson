
compiled = gnome.compile_schemas('com.github.meson.gschema.xml')
install_data('com.github.meson.gschema.xml',
install_dir : 'share/glib-2.0/schemas')

schemaexe = executable('schemaprog', 'schemaprog.c', compiled,
dependencies : gio)
test('schema test', schemaexe)
