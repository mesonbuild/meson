subdir('lib1')
subdir('lib2')
subdir('lib3')

main = executable('say', 'main.c', link_with: [lib2], include_directories: lib2_includes)

main_pot = i18n.xgettext('main', main, args: xgettext_args, install: true, install_dir: 'intl', install_tag: 'intl', recursive: true)

verify = find_program('verify.py')

# main links lib2 and lib2 links lib1, but main does not link lib1 directly.
# With recursive: true, the .pot must pick up lib1's "Something!" transitively
# through lib2, not just lib2's own "Something else!".
test(
    'recursive xgettext through static libraries',
    verify,
    args: [main_pot, 'Something else!', 'Something!'],
)
