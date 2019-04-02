project('python sample', 'c')

py_mod = import('python')
py = py_mod.find_installation('python3')

py_version = py.language_version()
if py_version.version_compare('< 3.2')
  error('MESON_SKIP_TEST python 3 required for tests')
endif

py_purelib = py.get_path('purelib')
if not py_purelib.endswith('site-packages')
  error('Python3 purelib path seems invalid? ' + py_purelib)
endif

# could be 'lib64' or 'Lib' on some systems
py_platlib = py.get_path('platlib')
if not py_platlib.endswith('site-packages')
  error('Python3 platlib path seems invalid? ' + py_platlib)
endif

main = files('prog.py')

test('toplevel', py, args : main)

subdir('subdir')
