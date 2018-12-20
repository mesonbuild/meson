project('proj', 'c')
subproject('sub')
libSub = dependency('sub', fallback: ['sub', 'libSub'])

exe = executable('prog', 'prog.c', dependencies: libSub)
test('subproject subdir', exe)

# Verify the subproject has placed dependency overrides
dependency('sub')
dependency('sub-1.0')
