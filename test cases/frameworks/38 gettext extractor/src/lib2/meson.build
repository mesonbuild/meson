lib2 = library('mylib2', 'lib2.c', include_directories: lib1_includes, link_with: lib1)
lib2_pot = xgettext.extract('lib2', lib2)
lib2_includes = include_directories('.')
