project('cython limited api', ['cython', 'c'],
  # setting limited_api in debug mode on Windows yields errors.
  default_options: ['buildtype=release']
)

cythonc = meson.get_compiler('cython')
if cythonc.version() < '3.0'
  error('MESON_SKIP_TEST: Cython compiler version does not support limited API')
endif

py3 = import('python').find_installation()

ext_mod = py3.extension_module('limited',
  'limited.pyx',
  limited_api: '3.7'
)

test('limited_api runner',
  py3,
  args : files('run.py'),
  env : ['PYTHONPATH=' + meson.current_build_dir()]
)
