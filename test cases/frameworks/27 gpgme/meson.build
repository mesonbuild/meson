project('gpgme test', 'c')

gpgme_dep = dependency('gpgme', version: '>= 1.0', required: false)
if not gpgme_dep.found()
  error('MESON_SKIP_TEST: gpgme not found')
endif

gpgme_ver = gpgme_dep.version()
assert(gpgme_ver.split('.').length() > 1, 'gpgme version is "@0@"'.format(gpgme_ver))
message('gpgme version is "@0@"'.format(gpgme_ver))
e = executable('gpgme_prog', 'gpgme_prog.c', dependencies: gpgme_dep)

test('gpgmetest', e)

# Test using the method keyword:

if find_program('gpgme-config', required: false).found()
  dependency('gpgme', method: 'config-tool')
  # Check we can apply a version constraint
  dependency('gpgme', version: '>=@0@'.format(gpgme_dep.version()), method: 'config-tool')
endif

# If newer gpgme has pkg-config metadata, make sure it is preferred by default:

gpgme_pc_dep = dependency('gpgme', method: 'pkg-config', required: false)
if gpgme_ver.version_compare('>=1.13.0') and gpgme_pc_dep.found()
  assert(gpgme_dep.type_name() == 'pkgconfig', 'dependency found via pkg-config')
endif
