import_dir_gen = protoc.generate(
  files('import_dir.proto'),
  language: 'cpp',
  install: true,
  install_dir: get_option('includedir') / 'import_dir',
)
import_dir_inc = include_directories('.')
