project('python extension', 'c', meson_version : '>=1.3.0')

py = import('python').find_installation('')

py.extension_module(
    'foo', 'foo.c',
    install: true,
)

limited_api_supported = true
if py.language_version().version_compare('>=3.13') and py.language_version().version_compare('<3.15')
  limited_api_supported = py.get_variable('Py_GIL_DISABLED') != 1
endif
if limited_api_supported
  py.extension_module(
      'foo_stable', 'foo.c',
      install: true,
      limited_api: '3.2',
  )
endif
