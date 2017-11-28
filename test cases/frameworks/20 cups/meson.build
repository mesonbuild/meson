project('cups test', 'c')

cups_dep = dependency('cups', version : '>=1.4')

e = executable('cups_prog', 'cups_prog.c', dependencies : cups_dep)

test('cupstest', e)

# ensure we can find the cups dependency via the legacy and modern config-tool
# options
dep = dependency('cups', version : '>=1.4', method : 'cups-config')
dep = dependency('cups', version : '>=1.4', method : 'config-tool')
