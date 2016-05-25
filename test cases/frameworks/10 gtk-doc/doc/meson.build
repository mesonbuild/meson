cdata = configuration_data()
cdata.set('VERSION', '1.0')
configure_file(input : 'version.xml.in',
  output : 'version.xml',
  configuration : cdata)

gnome.gtkdoc('foobar', src_dir : inc, main_sgml : 'foobar-docs.sgml', install : true)
