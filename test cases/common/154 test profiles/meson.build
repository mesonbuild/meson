project('test project', 'c',
  version: '1'
)

configure_file(
  input: 'file.in',
  output: 'file.out',
  configuration: configuration_data()
)

test = executable('test-exe', 'test.c',
  dependencies: dependency('glib-2.0')
)

test('Test GLib (with env dict)', test, profile: 'glib', env: 'foo=bar')
test('Test GLib (with env object)', test, profile: 'glib', env: environment())