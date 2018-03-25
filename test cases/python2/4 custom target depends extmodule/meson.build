project('Python extension module', 'c',
  default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

py2_mod = import('python2')
py2 = py2_mod.find_python()
py2_dep = dependency('python2', required : false)

# Copy to the builddir so that blaster.py can find the built tachyon module
# FIXME: We should automatically detect this case and append the correct paths
# to PYTHONLIBDIR
blaster_py = configure_file(input : 'blaster.py',
                            output : 'blaster.py',
                            configuration : configuration_data())

check_exists = '''
import os, sys
with open(sys.argv[1], 'rb') as f:
  assert(f.read() == b'success')
'''
if py2_dep.found()
  subdir('ext')

  out_txt = custom_target('tachyon flux',
    input : blaster_py,
    output : 'out.txt',
    command : [py2, '@INPUT@', '-o', '@OUTPUT@'],
    depends : pylib,
    build_by_default: true)

  test('flux', py2, args : ['-c', check_exists, out_txt])
else
  error('MESON_SKIP_TEST: Python2 libraries not found, skipping test.')
endif
