# Test that we can build a library that uses the limited API
# and link it to an extension module.

project('Python limited api lib', 'c',
  default_options : ['buildtype=release', 'werror=true'])

py_mod = import('python')
py = py_mod.find_installation(limited_api: '3.7')
py_dep = py.dependency(required: true)

nanolib = static_library(
    'nanolib',
    'nanolib.c',
    dependencies: [py_dep],
)

ext_mod = py.extension_module('mymodule',
  'module.c',
  install: true,
  link_with: [nanolib],
)

test('load-test',
  py,
  args: [files('test_module.py')],
  env: { 'PYTHONPATH': meson.current_build_dir() },
  workdir: meson.current_source_dir()
)
