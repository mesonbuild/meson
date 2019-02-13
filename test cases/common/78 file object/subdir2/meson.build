my_include_dir = join_paths(include_dir, 'subdir2')

prog2 = files('prog.c')
lib2 = files('lib.c')

test('subdir3', executable('subdir3', prog1, lib2), should_fail : true)
test('subdir4', executable('subdir4', prog2, lib1, include_directories: my_include_dir), should_fail : true)

test('subdir4', executable('subdir5', prog2, lib2, include_directories: my_include_dir))
