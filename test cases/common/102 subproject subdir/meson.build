project('proj', 'c')
subproject('sub')
libSub = dependency('sub', fallback: ['sub', 'libSub'])

exe = executable('prog', 'prog.c', dependencies: libSub)
test('subproject subdir', exe)

# Verify the subproject has placed dependency override.
dependency('sub-1.0')

# Verify we can now take 'sub' dependency without fallback, but only version 1.0.
dependency('sub')
d = dependency('sub', version : '>=2.0', required : false)
assert(not d.found(), 'version should not match')

# Verify that not-found does not get cached, we can still fallback afterward.
dependency('sub2', required : false)
d = dependency('sub2', fallback: ['sub', 'libSub'])
assert(d.found(), 'Should fallback even if a previous call returned not-found')

# Verify we can get a fallback dependency without specifying the variable name,
# because the subproject overridden 'sub-novar'.
dependency('sub-novar', fallback : 'sub_novar')

# Verify a subproject can force a dependency to be not-found
d = dependency('sub-notfound', fallback : 'sub_novar', required : false)
assert(not d.found(), 'Dependency should be not-found')
