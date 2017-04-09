l = shared_library('valalib', 'mylib.vala', dependencies : valadeps)

shared_library('installed_vala_lib', 'mylib.vala',
  dependencies : valadeps,
  install : true)

shared_library('installed_vala_all', 'mylib.vala',
  dependencies : valadeps,
  install : true,
  install_dir : [true, true, true])

shared_library('installed_vala_all_nolib', 'mylib.vala',
  dependencies : valadeps,
  install : true,
  install_dir : [false,
                 join_paths(get_option('includedir'), 'valah'),
                 join_paths(get_option('datadir'), 'vala-1.0', 'vapi')])

shared_library('installed_vala_onlyh', 'mylib.vala',
  dependencies : valadeps,
  install : true,
  install_dir : [false, get_option('includedir'), false])

shared_library('installed_vala_onlyvapi', 'mylib.vala',
  dependencies : valadeps,
  install : true,
  install_dir : [false, false, join_paths(get_option('datadir'), 'vala', 'vapi')])
