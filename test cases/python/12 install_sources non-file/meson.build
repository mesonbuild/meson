project('install_sources non-file')

py = import('python').find_installation()

custom = custom_target(
    output: 'gluon.py',
    command: [
        find_program('touch'),
        '@OUTPUT@',
    ],
)

py.install_sources(custom)
