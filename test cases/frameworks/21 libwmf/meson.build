project('libwmf test', 'c')

libwmf_dep = dependency('libwmf', version : '>= 0.2.8', required : false)
if not libwmf_dep.found()
  error('MESON_SKIP_TEST: libwmf not installed')
endif

libwmf_ver = libwmf_dep.version()
assert(libwmf_ver.split('.').length() > 1, 'libwmf version is "@0@"'.format(libwmf_ver))
message('libwmf version is "@0@"'.format(libwmf_ver))
# Workaround for Debian bug 912563 where libwmf-devel returns cflags
# that do not have Freetype include paths but their headers
# use them unconditionally.
ft_dep = dependency('freetype2')
e = executable('libwmf_prog', 'libwmf_prog.c', dependencies : [libwmf_dep, ft_dep])

test('libwmftest', e)

# Check we can apply a version constraint
dependency('libwmf', version: '>=@0@'.format(libwmf_ver), method: 'pkg-config', required: false)

# Test using the method keyword. Only exercise the config-tool method when
# libwmf-config is actually available on PATH.
libwmf_config = find_program('libwmf-config', required : false)
if libwmf_config.found() and not meson.is_cross_build()
  dependency('libwmf', method : 'config-tool')
  dependency('libwmf', method : 'libwmf-config')
  dependency('libwmf', version: '>=@0@'.format(libwmf_ver), method: 'config-tool')
endif
