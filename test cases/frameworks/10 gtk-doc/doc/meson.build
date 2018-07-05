cdata = configuration_data()
cdata.set('VERSION', '1.0')
version_xml = configure_file(input : 'version.xml.in',
                             output : 'version.xml',
                             configuration : cdata)

gnome.gtkdoc('foobar',
  src_dir : inc,
  main_sgml : 'foobar-docs.sgml',
  content_files : [docbook, version_xml],
  install : true)

gnome.gtkdoc('foobar2',
  src_dir : inc,
  main_sgml : 'foobar-docs.sgml',
  content_files : [docbook, version_xml],
  install : true,
  install_dir : 'foobar2')
