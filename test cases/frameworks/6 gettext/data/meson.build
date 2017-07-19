i18n.merge_file(
  input: 'test.desktop.in',
  output: 'test-old.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

data_files = i18n.files(
  'test.desktop.in',
  suffix: '.in',
  language: 'desktop',
  keywords: [ '', 'NonStandardKey' ],
  merge: true,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)
