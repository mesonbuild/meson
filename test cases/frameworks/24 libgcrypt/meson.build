project('libgcrypt test', 'c')

wm = find_program('libgcrypt-config', required : false)
dep = dependency('libgcrypt', method: 'pkg-config', required: false)
if not wm.found() and not dep.found()
  error('MESON_SKIP_TEST: libgcrypt-config not installed')
endif

libgcrypt_dep = dependency('libgcrypt', version : '>= 1.0')
libgcrypt_ver = libgcrypt_dep.version()
assert(libgcrypt_ver.split('.').length() > 1, 'libgcrypt version is "@0@"'.format(libgcrypt_ver))
message('libgcrypt version is "@0@"'.format(libgcrypt_ver))
e = executable('libgcrypt_prog', 'libgcrypt_prog.c', dependencies : libgcrypt_dep)

test('libgcrypttest', e)

# Test using the method keyword:

lct = dependency('libgcrypt', method : 'config-tool', required: false)
pct = dependency('libgcrypt', method : 'pkg-config', required: false)
if not lct.found() and not pct.found()
  error('libgcrypt not found')
endif

# Check we can apply a version constraint
lctv = dependency('libgcrypt', version: '>=@0@'.format(libgcrypt_dep.version()), method: 'pkg-config', required: false)
pctv = dependency('libgcrypt', version: '>=@0@'.format(libgcrypt_dep.version()), method: 'config-tool', required: false)
if not lct.found() and not pct.found()
  error('libgcrypt version constraint not working as expected')
endif
