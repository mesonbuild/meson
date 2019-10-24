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

py.custom_target(
  'test automatic depfile',
  output : 'testgendep',
  command : [files('testgen.py'), '@OUTPUT@'],
)

gen = py.generator(
  files('testgen.py'),
  output : '@BASENAME@.out',
  arguments : ['@OUTPUT@', '@INPUT@'],
)

genout = gen.process('testgen.py')

custom_target(
  'fake',
  output : 'fake',
  command : 'fake',
  input : genout,
)

main = files('prog.py')

test('toplevel', py, args : main)

subdir('subdir')
