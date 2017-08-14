project('reserved target names', 'c')
        # FIXME: Setting this causes it to leak to all other tests
        #default_options : ['b_coverage=true']

subdir('all')
subdir('benchmark')
subdir('clean')
subdir('clean-ctlist')
subdir('clean-gcda')
subdir('clean-gcno')
subdir('coverage')
subdir('coverage-html')
subdir('coverage-text')
subdir('coverage-xml')
subdir('dist')
subdir('distcheck')
subdir('install')
# We end up creating duplicate lowercase target names for this on
# case-insensitive HFS+, so disable it
# https://travis-ci.org/mesonbuild/meson/jobs/264468097
#subdir('phony')
subdir('PHONY')
subdir('reconfigure')
subdir('scan-build')
subdir('test')
subdir('uninstall')

subdir('runtarget')

custom_target('ctlist-test', output : 'out.txt',
              command : ['echo'], capture : true,
              build_by_default : true)
