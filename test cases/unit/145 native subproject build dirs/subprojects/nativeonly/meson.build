project('native only', 'c')

subdir('gen')

executable('main', 'main.c',
    include_directories: include_directories('gen'),
    c_args: '-DEXPECTED=@0@'.format(meson.is_cross_build() ? 1 : 0),
)
