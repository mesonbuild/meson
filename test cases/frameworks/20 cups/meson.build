project('cups test', 'c')

cups_dep = dependency('cups', version : '>=1.4', required: false)

if not cups_dep.found()
  error('MESON_SKIP_TEST cups not found.')
endif

e = executable('cups_prog', 'cups_prog.c', dependencies : cups_dep)

test('cupstest', e)

# ensure we can find the cups dependency via the legacy and modern config-tool
# options
dep = dependency('cups', version : '>=1.4', method : 'cups-config')
dep = dependency('cups', version : '>=1.4', method : 'config-tool')

# check we can apply a version constraint
dependency('cups', version: '>=@0@'.format(dep.version()), method: 'pkg-config', required: false)
dependency('cups', version: '>=@0@'.format(dep.version()), method: 'config-tool')
