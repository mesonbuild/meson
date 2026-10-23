project('override from failed subproject', 'c')

# 'failing' configures 'subsub' as a fallback, and then fails.
subproject('failing', required : false)

# 'subsub' is still configured, so its overrides must still be visible.
# 1.11 broke this
dep = dependency('subsub', fallback : ['subsub'], required: true)

e = executable('prog', 'prog.c', dependencies : dep, install: true)
test('prog', e)
