project('uninstalled env')

meson.add_uninstalled_environment('TEST_A=1')
subproject('sub')
meson.add_uninstalled_environment({'TEST_B': ['2', '3']}, method: 'append', separator:'+')
meson.add_uninstalled_environment(environment('TEST_B=0', method: 'prepend', separator:'+'))
