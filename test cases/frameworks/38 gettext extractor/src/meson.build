subdir('lib1')
subdir('lib2')
subdir('lib3')

main = executable('say', 'main.c', link_with: [lib2], include_directories: lib2_includes)

main_pot = i18n.xgettext('main', main, args: xgettext_args, install: true, install_dir: 'intl', install_tag: 'intl', recursive: true)

shmain = executable('shsay', 'main.c', link_with: [shlib2], include_directories: lib2_includes)
shmain_pot = i18n.xgettext('shmain', shmain, args: xgettext_args, recursive: true)

verify = find_program('verify.py')

# main links lib2 and lib2 links lib1, but main does not link lib1 directly.
# With recursive: true, the .pot must pick up lib1's "Something!" transitively
# through lib2, not just lib2's own "Something else!".
test(
    'recursive xgettext through static libraries',
    verify,
    args: [main_pot, 'Something else!', 'Something!'],
)

# Same chain, but with shared libraries. Unlike static libraries, shared
# libraries do not pull in their dependencies' objects, so shlib1 is not part
# of shmain.get_dependencies(). Recursive xgettext must still descend through
# shlib2 to reach shlib1's strings.
test(
    'recursive xgettext through shared libraries',
    verify,
    args: [shmain_pot, 'Something else!', 'Something!'],
)
