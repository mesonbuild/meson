project('b0rken', 'c', default_options: ['default_library=both'])
foo = both_libraries('foo', 'foo.c')

build_target('bt_both', 'b.c', target_type: 'both_libraries', link_whole: foo)
build_target('bt_lib', 'b.c', target_type: 'library', link_whole: foo)
build_target('bt_static', 'b.c', target_type: 'static_library', link_whole: foo)
build_target('bt_shared', 'b.c', target_type: 'shared_library', link_whole: foo)
build_target('bt_exe', 'exe.c', target_type: 'executable', link_whole: foo)

both_libraries('both', 'b.c', link_whole: foo)
library('lib', 'b.c', link_whole: foo)
static_library('static', 'b.c', link_whole: foo)
shared_library('shared', 'b.c', link_whole: foo)
executable('exe', 'exe.c', link_whole: foo)
