project('cups test', 'c')

cups_dep = dependency('cups', version : '>=1.4')

e = executable('cups_prog', 'cups_prog.c', dependencies : cups_dep)

test('cupstest', e)
