project('invalid build_subdir test', 'c', meson_version : '>= 1.9.1')

# This setup intentially tries to use a build_subdir
# with a name matching one in the source directory.
# produce a Ninja targets with the same name. It only works on
# unix, because on Windows the target has a '.exe' suffix.
#
# This test might fail to work on different backends or when
# output location is redirected.

conf = configuration_data()

conf.set('var', 'mystring')
conf.set('other', 'string 2')
conf.set('second', ' bonus')
conf.set('BE_TRUE', true)

configure_file(input : files('existing-dir/config.h.in'),
               output : 'config.h',
               build_subdir : 'existing-dir',
               install_dir : 'share/appdir/existing-dir',
               configuration : conf)

run_target('build_dir', command: ['echo', 'clash 1'])
