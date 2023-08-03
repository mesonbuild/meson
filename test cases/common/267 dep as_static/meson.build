project(
    'as_static',
    ['c'],
    meson_version: '>= 1.3.0',
)

lib1 = library('lib1', 'lib1.c', vs_module_defs: 'lib1.def', c_static_args: ['-DNUMBER=100'], c_shared_args: ['-DNUMBER=1000'])
dep1 = declare_dependency(link_with: lib1)

lib2 = both_libraries('lib2', 'lib2.c', vs_module_defs: 'lib2.def', c_static_args: ['-DNUMBER=100'], c_shared_args: ['-DNUMBER=1000'])
dep2 = declare_dependency(link_with: lib2)

lib3 = shared_library('lib3', 'lib3.c', vs_module_defs: 'lib3.def')
dep3 = declare_dependency(link_with: lib3)

lib4 = static_library('lib4', 'lib4.c')
dep4 = declare_dependency(link_with: lib4)


if get_option('default_library') == 'static'
    lib1_n = 101
else
    lib1_n = 1001  # shared or both will use shared
endif
lib2_n = 1002  # shared
lib3_n = 3
lib4_n = 4

expected = lib1_n + lib2_n + lib3_n + lib4_n
dep_default = declare_dependency(dependencies: [dep1, dep2, dep3, dep4])
main_default = executable('main_default', 'main.c', dependencies: [dep_default], c_args: ['-DEXPECTED=@0@'.format(expected)])
test('default', main_default)


if get_option('default_library') == 'shared'
    lib1_n = 1001
else
    lib1_n = 101  # static or both will use static
endif
lib2_n = 102  # static
lib3_n = 3
lib4_n = 4

expected = lib1_n + lib2_n + lib3_n + lib4_n
dep_static = declare_dependency(dependencies: [dep1, dep2, dep3, dep4]).as_static(recursive: true)
main_static = executable('main_static', 'main.c', dependencies: [dep_static], c_args: ['-DEXPECTED=@0@'.format(expected)])
test('static', main_static)
