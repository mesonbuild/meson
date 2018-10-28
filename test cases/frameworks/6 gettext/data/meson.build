# Use filename substitution
i18n.merge_file(
  input: 'test.desktop.in',
  output: '@BASENAME@',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

# Use filename substitution for another file
i18n.merge_file(
  input: files('test2.desktop.in'),
  output: '@BASENAME@',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

i18n.merge_file(
  input: 'test.desktop.in',
  output: 'test3.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

subdir('data3')
