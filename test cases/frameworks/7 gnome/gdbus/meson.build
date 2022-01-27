gdbus_src = gnome.gdbus_codegen('generated-gdbus-no-docbook',
  'data/com.example.Sample.xml',
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [
    ['com.example.Hello()', 'org.freedesktop.DBus.Deprecated', 'true']
  ],
)

# check that empty annotations work
gdbus_src2 = gnome.gdbus_codegen(
  'generated-gdbus-no-docbook2',
  'data/com.example.Sample.xml',
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [],
)

assert(gdbus_src.length() == 2, 'expected 2 targets')
assert(gdbus_src[0].full_path().endswith('.c'), 'expected 1 c source file')
assert(gdbus_src[1].full_path().endswith('.h'), 'expected 1 c header file')

sample_xml = configure_file(input: 'data/com.example.Sample.xml',
  output: 'com.example.Sample.xml',
  copy: true)

gdbus_src = gnome.gdbus_codegen('generated-gdbus-no-docbook-files-posarg',
  sample_xml,
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [
    ['com.example.Hello()', 'org.freedesktop.DBus.Deprecated', 'true']
  ],
)
assert(gdbus_src.length() == 2, 'expected 2 targets')
assert(gdbus_src[0].full_path().endswith('.c'), 'expected 1 c source file')
assert(gdbus_src[1].full_path().endswith('.h'), 'expected 1 c header file')

gdbus_src = gnome.gdbus_codegen('generated-gdbus',
  sources : files('data/com.example.Sample.xml'),
  interface_prefix : 'com.example.',
  namespace : 'Sample',
  annotations : [
    ['com.example.Hello()', 'org.freedesktop.DBus.Deprecated', 'true'],
    ['com.example.Bye()', 'org.freedesktop.DBus.Deprecated', 'true'],
  ],
  docbook : 'generated-gdbus-doc',
  install_header : true,
  install_dir : get_option('includedir')
)
assert(gdbus_src.length() == 3, 'expected 3 targets')
assert(gdbus_src[0].full_path().endswith('.c'), 'expected 1 c source file')
assert(gdbus_src[1].full_path().endswith('.h'), 'expected 1 c header file')

if not pretend_glib_old and glib.version().version_compare('>=2.51.3')
  includes = []
else
  includes = include_directories('..')
endif

gdbus_exe = executable('gdbus-test', 'gdbusprog.c',
  gdbus_src,
  include_directories : includes,
  dependencies : giounix)

test('gdbus', gdbus_exe)
