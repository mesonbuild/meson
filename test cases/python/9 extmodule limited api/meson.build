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

# A library (not an extension module) built against the limited API
py_dep_limited = py.dependency(limited_api: '3.7')

limited_dependency = static_library('limited_dependency',
  'limited_lib.c',
  dependencies: [py_dep_limited],
)

# Check that limited_api is inherited by the dependency
py_limited = py_mod.find_installation(limited_api: '3.7')

static_library('limited_dependency_inherited',
  'limited_lib.c',
  dependencies: [py_limited.dependency()],
)

static_library('not_limited_dependency_inherited_overridden',
  'not_limited.c',
  dependencies: [py_limited.dependency(limited_api: '')],
)

# Check that limited_api is inherited by the extension
py_limited.extension_module('limited_inherited',
  'limited.c',
  install: true,
)

py_limited.extension_module('not_limited_inherited_overridden',
  'not_limited.c',
  install: true,
  limited_api: '',
)

# Check that a limited extension swaps out a not-limited dependency
py.extension_module('limited_with_not_limited_dep',
  'limited.c',
  limited_api: '3.7',
  dependencies: [py.dependency()],
)

# Check that a not-limited extension swaps out a limited dependency
py.extension_module('not_limited_with_limited_dep',
  'not_limited.c',
  dependencies: [py.dependency(limited_api: '3.7')],
)

# Check that a limited extension can link a limited library
py.extension_module('limited_with_lib',
  'limited_with_lib.c',
  limited_api: '3.7',
  link_with: [limited_dependency],
  install: true,
)
