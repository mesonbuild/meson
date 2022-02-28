project('subproject dependency variables', 'c')

subfiles_dep = subproject('subfiles').get_variable('files_dep')

executable(
    'foo',
    join_paths(subfiles_dep.get_variable('pkgdatadir'), 'foo.c')
)

executable(
    'foo2',
    subfiles_dep.get_variable('pkgdatadir2') / 'foo.c'
)
