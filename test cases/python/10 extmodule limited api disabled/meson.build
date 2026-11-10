project('Python limited api disabled', 'c',
  default_options : ['buildtype=release', 'werror=true', 'python.allow_limited_api=false'])

py_mod = import('python')
py = py_mod.find_installation()

module = py.extension_module('my_module',
  'module.c',
  limited_api: '3.7',
)

py_limited = py_mod.find_installation(limited_api: '3.7')

module = py_limited.extension_module('my_module_inherited',
  'module.c',
)
