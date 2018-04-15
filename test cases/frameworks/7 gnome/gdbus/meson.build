gdbus_src = gnome.gdbus_codegen('generated-gdbus-no-docbook', 'com.example.Sample.xml',
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [
    ['com.example.Hello()', 'org.freedesktop.DBus.Deprecated', 'true']
  ],
)
assert(gdbus_src.length() == 2, 'expected 2 targets')

gdbus_src = gnome.gdbus_codegen('generated-gdbus',
  sources : 'com.example.Sample.xml',
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [
    ['com.example.Hello()', 'org.freedesktop.DBus.Deprecated', 'true']
  ],
  docbook : 'generated-gdbus-doc'
)
assert(gdbus_src.length() == 3, 'expected 3 targets')

gdbus_exe = executable('gdbus-test', 'gdbusprog.c',
  gdbus_src,
  include_directories : include_directories('..'),
  dependencies : giounix)

test('gdbus', gdbus_exe)
