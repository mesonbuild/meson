lib1 = static_library('mylib1', 'lib1.c')
lib1_pot = i18n.xgettext('lib1', lib1, args: xgettext_args)
lib1_includes = include_directories('.')

# Shared-library variant of the same chain, used to test that recursive
# xgettext descends through shared libraries (which, unlike static libraries,
# do not pull in their dependencies' objects).
shlib1 = shared_library('myshlib1', 'lib1.c')
shlib1_pot = i18n.xgettext('shlib1', shlib1, args: xgettext_args)
