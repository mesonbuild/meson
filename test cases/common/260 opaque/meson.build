project('opaque_gen', 'c')

opaque_target('datagen',
    command: [find_program('ersatz_doctool.py')],
    args: ['--foobar'],
    install: true,
    install_dir: get_option('datadir') / 'doc'
)
