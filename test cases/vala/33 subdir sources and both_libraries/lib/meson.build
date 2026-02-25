args = []
# https://github.com/mesonbuild/meson/issues/1969
if get_option('unity') == 'on'
  vala_args = ['-H', 'mylib.h']
endif

l = both_libraries('valalib', 'subdir/mylib.vala',
                   vala_args : args,
                   dependencies : valadeps,
                   install_dir : [false, get_option('includedir'), false])
