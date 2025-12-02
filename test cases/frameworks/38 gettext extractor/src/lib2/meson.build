lib2 = static_library('mylib2', 'lib2.c', include_directories: lib1_includes, link_with: lib1)
lib2_pot = i18n.xgettext('lib2', lib2, args: xgettext_args)
lib2_includes = include_directories('.')

shlib2 = shared_library('myshlib2', 'lib2.c', include_directories: lib1_includes, link_with: shlib1)
shlib2_pot = i18n.xgettext('shlib2', shlib2, args: xgettext_args)
