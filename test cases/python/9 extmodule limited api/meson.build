project('Python limited api', 'c',
  default_options : ['buildtype=release', 'werror=true'])

py_mod = import('python')
py = py_mod.find_installation()

if py.get_variable('Py_GIL_DISABLED', 0) == 1 and py.language_version().version_compare('<3.15')
  error('MESON_SKIP_TEST: Freethreading Python does not support limited API')
endif

ext_mod_limited = py.extension_module('limited',
  'limited.c',
  limited_api: '3.7',
  install: true,
)

ext_mod = py.extension_module('not_limited',
  'not_limited.c',
  install: true,
)

test('load-test',
  py,
  args: [files('test_limited.py')],
  env: { 'PYTHONPATH': meson.current_build_dir() },
  workdir: meson.current_source_dir()
)
