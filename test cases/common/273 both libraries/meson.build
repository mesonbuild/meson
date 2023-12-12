project(
    'test both libraries',
    'c',
    meson_version: '>= 1.6.0',
)

expected = 0


with_library = library(
    'with_library',
    files('src/library.c'),
    c_shared_args: ['-DEXPORT'],
)

with_library_dep = declare_dependency(
    link_with: with_library,
)

if get_option('default_library') == 'shared'
    expected += 1
elif get_option('default_library') == 'both'
    if get_option('default_both_libraries') in ['shared', 'auto']
        expected += 1
    endif
endif



mainlink = executable(
    'mainlink',
    files('src/main.c'),
    c_args: [f'-DEXPECTED=@expected@'],
    link_with: [with_library],
)
test('link with', mainlink)

maindep = executable(
    'maindep',
    files('src/main.c'),
    c_args: [f'-DEXPECTED=@expected@'],
    dependencies: [with_library_dep],
)
test('use dep', maindep)
