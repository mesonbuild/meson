project('gpgme test', 'c')

wm = find_program('gpgme-config', required: false)
if not wm.found()
  error('MESON_SKIP_TEST: gpgme-config not installed')
endif

gpgme_dep = dependency('gpgme', version: '>= 1.0')
gpgme_ver = gpgme_dep.version()
assert(gpgme_ver.split('.').length() > 1, 'gpgme version is "@0@"'.format(gpgme_ver))
message('gpgme version is "@0@"'.format(gpgme_ver))
e = executable('gpgme_prog', 'gpgme_prog.c', dependencies: gpgme_dep)

test('gpgmetest', e)

# Test using the method keyword:

dependency('gpgme', method: 'config-tool')

# Check we can apply a version constraint
dependency('gpgme', version: '>=@0@'.format(gpgme_dep.version()), method: 'config-tool')
