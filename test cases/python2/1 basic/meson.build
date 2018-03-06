project('python sample', 'c')

py2_mod = import('python2')
py2 = py2_mod.find_python()

py2_version = py2_mod.language_version()
if py2_version.version_compare('< 2.7')
  error('Invalid python version!?')
endif

# These two paths can start with local, lib or lib64 on some systems;
# let's just check that they are relative
py2_purelib = py2_mod.sysconfig_path('purelib')
if py2_purelib.to_lower().startswith('/')
  if not py2_purelib.endswith('site-packages') and not py2_purelib.endswith('dist-packages')
    error('Python2 purelib path: [@0@] seems invalid?'.format(py2_purelib))
  endif
endif

py2_platlib = py2_mod.sysconfig_path('platlib')
if py2_platlib.to_lower().startswith('/')
  if not py2_platlib.endswith('site-packages') and not py2_platlib.endswith('dist-packages')
    error('Python2 platlib path: [@0@] seems invalid?'.format(py2_platlib))
  endif
endif

# could be 'Include' on Windows
py2_include = py2_mod.sysconfig_path('include')
if not py2_include.to_lower().startswith('include')
  error('Python2 include path: [@0@] seems invalid?'.format(py2_include))
endif

main = files('prog.py')

test('toplevel', py2, args : main)

subdir('subdir')
