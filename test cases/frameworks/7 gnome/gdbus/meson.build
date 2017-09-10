gdbus_src = gnome.gdbus_codegen('generated-gdbus', 'com.example.Sample.xml',
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [
    ['com.example.Hello()', 'org.freedesktop.DBus.Deprecated', 'true']
  ],
  docbook : 'generated-gdbus-doc'
)

gdbus_exe = executable('gdbus-test', 'gdbusprog.c',
  gdbus_src,
  include_directories : include_directories('..'),
  dependencies : giounix)

test('gdbus', gdbus_exe)
