subdir('lib1')
subdir('lib2')

main = executable('say', 'main.c', link_with: [lib2], include_directories: lib2_includes)

main_pot = xgettext.extract('main', main, install: true, install_dir: 'intl', install_tag: 'intl', merge: true)
