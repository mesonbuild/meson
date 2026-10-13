cdata = configuration_data()
cdata.set('VERSION', '1.0')
version_xml = configure_file(input : 'version.xml.in',
                             output : 'version.xml',
                             configuration : cdata)

subdir('foobar1')
subdir('foobar2')
subdir('foobar3')
subdir('foobar4')

testcase expect_error('gnome.gtkdoc: one of main_xml or main_sgml is required')
  gnome.gtkdoc('nomainfile', src_dir: inc)
endtestcase
