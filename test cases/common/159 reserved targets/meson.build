project('reserved target names', 'c',
        default_options : ['b_coverage=true'])

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
subdir('phony')
subdir('PHONY')
subdir('reconfigure')
subdir('scan-build')
subdir('test')
subdir('uninstall')

subdir('runtarget')

custom_target('ctlist-test', output : 'out.txt',
              command : ['echo'], capture : true,
              build_by_default : true)
