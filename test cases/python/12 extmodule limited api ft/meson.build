project('Python limited api ft', 'c',
  default_options : ['buildtype=release', 'werror=true'])

py_mod = import('python')
py = py_mod.find_installation()

if py.language_version().version_compare('<3.15')
  error('MESON_SKIP_TEST: Py_TARGET_ABI3T is supported since 3.15.0a8')
endif

ext_mod_limited = py.extension_module('limited',
  'limited.c',
  limited_api: '3.15',
  install: true,
)

test('load-test',
  py,
  args: [files('test_limited.py')],
  env: { 'PYTHONPATH': meson.current_build_dir() },
  workdir: meson.current_source_dir()
)
