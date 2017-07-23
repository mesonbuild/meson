marshallers = gnome.genmarshal('marshaller',
sources : 'marshaller.list',
install_header : true,
install_dir : get_option('includedir'),
extra_args : ['-UG_ENABLE_DEBUG', '--prototypes'])

marshaller_c = marshallers[0]
marshaller_h = marshallers[1]

genmarshalexe = executable('genmarshalprog', 'main.c', marshaller_c, marshaller_h,
dependencies : gobj)
test('genmarshal test', genmarshalexe)
