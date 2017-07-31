project('conf file in test')

test_file = configure_file(
  input: 'test.py.in',
  output: 'test.py',
  configuration: configuration_data()
)

test('configure-file', test_file)
