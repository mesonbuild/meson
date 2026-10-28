project('dependency extra files', 'c')

dep = declare_dependency(extra_files: files('dep.txt'))
executable('prog', 'main.c', dependencies: dep, extra_files: files('own.txt'))
