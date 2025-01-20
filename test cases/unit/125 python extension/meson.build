project('python extension', 'c')

py = import('python').find_installation('')

py.extension_module(
    'foo', 'foo.c',
    install: true,
)

py.extension_module(
    'foo_stable', 'foo.c',
    install: true,
    limited_api: '3.2',
)

