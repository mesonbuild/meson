project('libwmf test', 'c')

method = get_option('method')

libwmf_dep = dependency('libwmf', method : method, required : false, version : '>= 0.2.8')

if not libwmf_dep.found()
  error(f'MESON_SKIP_TEST libwmf not found for method {method}.')
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
dependency('libwmf', version: '>=@0@'.format(libwmf_dep.version()), method : method)
