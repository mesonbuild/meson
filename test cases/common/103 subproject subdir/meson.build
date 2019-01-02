project('proj', 'c')
subproject('sub')
libSub = dependency('sub', fallback: ['sub', 'libSub'])

exe = executable('prog', 'prog.c', dependencies: libSub)
test('subproject subdir', exe)

# The dependency should be cached now, so should be found even without fallback
dependency('sub')

# Make sure we cannot override the special '' dependency
dependency('', fallback: ['sub', 'libSub'])
dep = dependency('', required : false)
assert(not dep.found(), 'The not-found dependency should not get cached')

# Make sure that if we first lookup for a dependency without fallback and the
# dependency was not found, subsequent calls still return not-found even when
# they provide a fallback
dependency('sub2', required : false)
dep = dependency('sub2', fallback: ['sub', 'libSub'], required : false)
assert(not dep.found(), 'A not found dependency should stay not found')
