project('proj', 'c')

sources = []
subdir('dir1')
subdir('dir2')
subdir('dir3')
executable('a.out', sources : sources, objects : lib.extract_all_objects())
