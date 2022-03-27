search_dir = get_option('search_dir')
if search_dir == 'auto'
  search_dir = meson.current_source_dir()
elif search_dir == 'none'
  search_dir = []
endif

cc = meson.get_compiler('c')
stlib = cc.find_library('best', dirs : search_dir)
stlib2 = cc.find_library('best', static : true, dirs : search_dir)

best_dep = declare_dependency(dependencies : stlib,
  include_directories : include_directories('.'))
best_dep2 = declare_dependency(dependencies : stlib2,
  include_directories : include_directories('.'))
