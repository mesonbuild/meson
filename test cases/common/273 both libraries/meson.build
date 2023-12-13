project(
    'test both libraries',
    'c',
    meson_version: '>= 1.6.0',
)

expected = 0


with_bl = both_libraries(
    'with_bl',
    files('src/both_libraries.c'),
    c_shared_args: ['-DEXPORT'],
)

with_bl_dep = declare_dependency(
    link_with: with_bl,
)


if get_option('use_dep')
    lib_deps = [with_bl_dep]
    lib_links = []
else
    lib_deps = []
    lib_links = [with_bl]
endif


with_library = library(
    'with_library',
    files('src/library.c'),
    c_shared_args: ['-DEXPORT'],
    link_with: lib_links,
    dependencies: lib_deps,
)

with_library_dep = declare_dependency(
    link_with: with_library,
)


if get_option('default_library') == 'shared'
    expected += 1
    if get_option('default_both_libraries') in ['shared', 'auto']
        expected += 1
    endif
elif get_option('default_library') == 'both'
    if get_option('default_both_libraries') in ['shared', 'auto']
        expected += 2
    endif
else
    if get_option('default_both_libraries') == 'shared'
        expected += 1
    endif
endif


if get_option('use_dep')
    main_deps = [with_library_dep]
    main_links = []
else
    main_deps = []
    main_links = [with_library]
endif

main = executable(
    'main',
    files('src/main.c'),
    c_args: [f'-DEXPECTED=@expected@'],
    link_with: main_links,
    dependencies: main_deps,
)
test('test both libs', main)


if get_option('default_library') == 'both' and get_option('default_both_libraries') == 'auto'
    # With those options, even if the both_libraries defaults to 'shared',
    # 'static' version is used when linking to the static part of another both_libraries.
    main_static = executable(
        'main_static',
        files('src/main.c'),
        c_args: [f'-DEXPECTED=0'],
        link_with: with_library.get_static_lib(),
    )
    test('test static', main_static)
endif
