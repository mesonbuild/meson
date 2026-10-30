project('sub', 'c', meson_version: '>=1.10.0')

subdir('gen')

executable('main', 'main.c',
    include_directories: include_directories('inc', 'gen/sub2'),
    c_args: '-DEXPECTED=@0@'.format(meson.is_cross_build() ? 1 : 0),
)
