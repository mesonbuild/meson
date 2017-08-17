project('python sample', 'c')

py3_mod = import('python3')
py3 = py3_mod.find_python()

py3_version = py3_mod.language_version()
if py3_version.version_compare('< 3.2')
  error('Invalid python version!?')
endif

py3_purelib = py3_mod.sysconfig_path('purelib')
if not py3_purelib.to_lower().startswith('lib') or not py3_purelib.endswith('site-packages')
  error('Python3 purelib path seems invalid?')
endif

# could be 'lib64' or 'Lib' on some systems
py3_platlib = py3_mod.sysconfig_path('platlib')
if not py3_platlib.to_lower().startswith('lib') or not py3_platlib.endswith('site-packages')
  error('Python3 platlib path seems invalid?')
endif

# could be 'Include' on Windows
py3_include = py3_mod.sysconfig_path('include')
if not py3_include.to_lower().startswith('include')
  error('Python3 include path seems invalid?')
endif

main = files('prog.py')

test('toplevel', py3, args : main)

subdir('subdir')
