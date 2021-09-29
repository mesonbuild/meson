project(
  'generated cython sources',
  ['cython'],
)

py_mod = import('python')
py3 = py_mod.find_installation('python3')
py3_dep = py3.dependency(required : false)
if not py3_dep.found()
  error('MESON_SKIP_TEST: Python library not found.')
endif

ct = custom_target(
  'ct',
  input : 'gen.py',
  output : 'ct.pyx',
  command : [py3, '@INPUT@', '@OUTPUT@'],
)

ct_ext = py3.extension_module('ct', ct, dependencies : py3_dep)

test(
  'custom target',
  py3,
  args : [files('test.py'), 'ct'],
  env : ['PYTHONPATH=' + meson.current_build_dir()]
)

# Test a CustomTargetIndex
cti = custom_target(
  'cti',
  input : 'gen.py',
  output : 'cti.pyx',
  command : [py3, '@INPUT@', '@OUTPUT@'],
)

cti_ext = py3.extension_module('cti', cti[0], dependencies : py3_dep)

cf = configure_file(
  input : 'configure.pyx.in',
  output : 'cf.pyx',
  copy : true,
)

cf_ext = py3.extension_module('cf', cf, dependencies : py3_dep)

test(
  'configure file',
  py3,
  args : [files('test.py'), 'cf'],
  env : ['PYTHONPATH=' + meson.current_build_dir()]
)

gen = generator(
  find_program('generator.py'),
  arguments : ['@INPUT@', '@OUTPUT@'],
  output : '@BASENAME@.pyx',
)

g_ext = py3.extension_module(
  'g',
  gen.process('g.in'),
  dependencies : py3_dep,
)

test(
  'generator',
  py3,
  args : [files('test.py'), 'g'],
  env : ['PYTHONPATH=' + meson.current_build_dir()]
)

subdir('libdir')

test(
  'custom target in subdir',
  py3,
  args : [files('test.py'), 'ct2'],
  env : ['PYTHONPATH=' + pydir]
)
