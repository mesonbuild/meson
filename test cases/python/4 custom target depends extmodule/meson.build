project('Python extension module', 'c',
  default_options : ['buildtype=release'])
# Because Windows Python ships only with optimized libs,
# we must build this project the same way.

py_mod = import('python')
py3 = py_mod.find_installation()
py3_dep = py3.dependency(required : false)

# Copy to the builddir so that blaster.py can find the built tachyon module
# FIXME: We should automatically detect this case and append the correct paths
# to PYTHONLIBDIR
blaster_py = configure_file(input : 'blaster.py',
                            output : 'blaster.py',
                            copy : true)

check_exists = '''
import os, sys
with open(sys.argv[1], 'rb') as f:
  assert(f.read() == b'success')
'''
if py3_dep.found()
  subdir('ext')

  out_txt = custom_target('tachyon flux',
    input : blaster_py,
    output : 'out.txt',
    command : [py3, '@INPUT@', '-o', '@OUTPUT@'],
    depends : pylib,
    build_by_default: true)

  test('flux', py3, args : ['-c', check_exists, out_txt])
else
  error('MESON_SKIP_TEST: Python3 libraries not found, skipping test.')
endif
