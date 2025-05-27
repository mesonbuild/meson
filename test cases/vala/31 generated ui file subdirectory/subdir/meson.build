ui_tgt = custom_target(
  input: 'TestBox.ui.in',
  output:  'TestBox.ui',
  command: [find_program('cat')],
  feed: true,
  capture: true,
)

resources = gnome.compile_resources('test-resources',
  'test.gresource.xml',
  c_name: 'test_res',
  dependencies: ui_tgt,
)
