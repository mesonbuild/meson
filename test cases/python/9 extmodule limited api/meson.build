project('Python limited api', 'c',
  default_options : ['buildtype=release', 'werror=true'])

py_mod = import('python')
py = py_mod.find_installation()

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

# Test inheritance and override of limited_api

py_limited = py_mod.find_installation(limited_api: '3.7')

py_limited.extension_module('limited_inherit',
  'limited.c',
)

py_limited.extension_module('not_limited_override',
  'not_limited.c',
  limited_api: '',
)

py_dep_limited = py.dependency(required: true, limited_api: '3.7')

static_library(
    'limited_dependency',
    'limited.c',
    dependencies: [py_dep_limited],
)

py_dep_inherit = py_limited.dependency(required: true)

static_library(
    'limited_dependency_inherit',
    'limited.c',
    dependencies: [py_dep_inherit],
)
