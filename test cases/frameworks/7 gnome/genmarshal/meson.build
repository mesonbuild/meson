marshaller_h = gnome.genmarshal('marshaller.h',
sources : 'marshaller.list',
header : true,
install : true,
install_dir : get_option('includedir'))

marshaller_c = gnome.genmarshal('marshaller.c',
sources : 'marshaller.list',
body : true)

genmarshalexe = executable('genmarshalprog', 'main.c', marshaller_c, marshaller_h,
dependencies : gobj)
test('genmarshal test', genmarshalexe)
