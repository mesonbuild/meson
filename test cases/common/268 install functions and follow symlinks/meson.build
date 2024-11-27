project('install_data following symlinks')

if build_machine.system() == 'windows'
    error('MESON_SKIP_TEST symlinks (typically) do not work on Windows.')
endif

install_data(
  'foo/link1',
  install_dir: get_option('datadir') / 'followed',
  follow_symlinks: true,
)

install_headers(
  'foo/link2.h',
  follow_symlinks: true,
  subdir: 'followed'
)

install_data(
  'foo/link1',
  install_dir: get_option('datadir'),
  follow_symlinks: false,
)

install_headers(
  'foo/link2.h',
  follow_symlinks: false,
)

install_subdir(
  'foo',
  install_dir: get_option('datadir') / 'subdir',
  strip_directory: true,
  follow_symlinks: false,
)

install_subdir(
  'foo',
  install_dir: get_option('datadir') / 'subdir_followed',
  strip_directory: true,
  follow_symlinks: true,
)
